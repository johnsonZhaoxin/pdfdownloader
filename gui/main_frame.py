# -*- coding: utf-8 -*-
"""主窗口：URL 输入、扫描、下载、归档、日志、进度。"""
import os
import threading

import wx

from config import DEFAULT_DOWNLOAD_DIR, ARCHIVE_KINDS
from core.fetcher import get_pdf_links, FetchError
from core.downloader import download_many
from core.organizer import organize_pdfs


class MainFrame(wx.Frame):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.SetSize((660, 540))
        self.SetMinSize((560, 460))

        self._links = []
        self._worker = None

        self._build_ui()
        self._build_menu()
        self.CreateStatusBar()
        self.SetStatusText("就绪")

    # ---------------- UI ----------------
    def _build_ui(self):
        panel = wx.Panel(self)
        root = wx.BoxSizer(wx.VERTICAL)

        title = wx.StaticText(panel, label="PDF 批量下载器")
        font = title.GetFont()
        font.PointSize += 8
        font = font.Bold()
        title.SetFont(font)
        root.Add(title, 0, wx.ALIGN_CENTER | wx.TOP | wx.BOTTOM, 12)

        # URL
        url_box = wx.BoxSizer(wx.HORIZONTAL)
        url_box.Add(wx.StaticText(panel, label="页面网址:"), 0,
                    wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        self.url_ctrl = wx.TextCtrl(panel)
        url_box.Add(self.url_ctrl, 1, wx.EXPAND)
        root.Add(url_box, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 12)

        # 目录
        dir_box = wx.BoxSizer(wx.HORIZONTAL)
        dir_box.Add(wx.StaticText(panel, label="保存目录:"), 0,
                    wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        self.dir_picker = wx.DirPickerCtrl(
            panel, path=DEFAULT_DOWNLOAD_DIR, message="选择保存目录")
        dir_box.Add(self.dir_picker, 1, wx.EXPAND)
        root.Add(dir_box, 0, wx.EXPAND | wx.ALL, 12)

        # 按钮
        btn_box = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_scan = wx.Button(panel, label="扫描链接")
        self.btn_download = wx.Button(panel, label="一键下载")
        self.btn_organize = wx.Button(panel, label="一键分类文件")
        self.btn_clear = wx.Button(panel, label="清空日志")
        btn_box.Add(self.btn_scan, 0, wx.RIGHT, 8)
        btn_box.Add(self.btn_download, 0, wx.RIGHT, 8)
        btn_box.Add(self.btn_organize, 0, wx.RIGHT, 8)
        btn_box.AddStretchSpacer()
        btn_box.Add(self.btn_clear, 0)
        root.Add(btn_box, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 12)

        # 进度
        self.gauge = wx.Gauge(panel, range=100)
        root.Add(self.gauge, 0, wx.EXPAND | wx.ALL, 12)

        # 日志
        self.log_ctrl = wx.TextCtrl(
            panel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
        root.Add(self.log_ctrl, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)

        panel.SetSizer(root)

        self.btn_scan.Bind(wx.EVT_BUTTON, self.on_scan)
        self.btn_download.Bind(wx.EVT_BUTTON, self.on_download)
        self.btn_organize.Bind(wx.EVT_BUTTON, self.on_organize)
        self.btn_clear.Bind(wx.EVT_BUTTON, lambda e: self.log_ctrl.Clear())

    def _build_menu(self):
        file_menu = wx.Menu()
        open_item = file_menu.Append(wx.ID_OPEN, "选择保存目录...\tCtrl-O")
        file_menu.AppendSeparator()
        exit_item = file_menu.Append(wx.ID_EXIT, "退出\tCtrl-Q")

        help_menu = wx.Menu()
        about_item = help_menu.Append(wx.ID_ABOUT, "关于")

        bar = wx.MenuBar()
        bar.Append(file_menu, "文件(&F)")
        bar.Append(help_menu, "帮助(&H)")
        self.SetMenuBar(bar)

        self.Bind(wx.EVT_MENU, self.on_choose_dir, open_item)
        self.Bind(wx.EVT_MENU, lambda e: self.Close(True), exit_item)
        self.Bind(wx.EVT_MENU, self.on_about, about_item)

    # ---------------- 工具 ----------------
    def _ui(self, fn, *a, **kw):
        wx.CallAfter(fn, *a, **kw)

    def log(self, msg):
        self._ui(self._log_sync, msg)

    def _log_sync(self, msg):
        self.log_ctrl.AppendText(msg + "\n")

    def _set_busy(self, busy):
        for b in (self.btn_scan, self.btn_download, self.btn_organize):
            b.Enable(not busy)
        self.SetStatusText("处理中..." if busy else "就绪")

    def _run_async(self, target):
        if self._worker and self._worker.is_alive():
            wx.MessageBox("已有任务正在进行", "提示", wx.OK | wx.ICON_WARNING)
            return
        self._set_busy(True)
        self.gauge.SetValue(0)

        def wrapped():
            try:
                target()
            except Exception as e:
                self.log(f"[异常] {e}")
            finally:
                self._ui(self._set_busy, False)

        self._worker = threading.Thread(target=wrapped, daemon=True)
        self._worker.start()

    # ---------------- 事件 ----------------
    def on_choose_dir(self, event):
        dlg = wx.DirDialog(self, "选择保存目录",
                           defaultPath=self.dir_picker.GetPath())
        if dlg.ShowModal() == wx.ID_OK:
            self.dir_picker.SetPath(dlg.GetPath())
        dlg.Destroy()

    def on_about(self, event):
        message = (
            "PDF 批量下载器\n\n"
            "· BeautifulSoup + 正则双策略抓取\n"
            "· 兼容 papacambridge download_file.php 与 Dropbox dl=1\n"
            "· 按试卷类型（ms/qp）自动归档\n"
            "· 文件名白名单过滤（er / gt / ms / qp）\n"
            "· 后台线程下载，UI 不卡顿\n\n"
            "赵三金开发，DeepSeek 改进"
        )
        wx.MessageBox(message, "关于", wx.OK | wx.ICON_INFORMATION)

    def on_scan(self, event):
        url = self.url_ctrl.GetValue().strip()
        if not url:
            wx.MessageBox("请先输入页面网址", "提示", wx.OK | wx.ICON_WARNING)
            return
        self._run_async(lambda: self._scan_worker(url))

    def _scan_worker(self, url):
        self.log(f"扫描页面: {url}")
        try:
            links = get_pdf_links(url)
        except FetchError as e:
            self.log(f"[失败] {e}")
            return
        self._links = links
        self.log(f"共发现 {len(links)} 个 PDF 链接")
        for u in links:
            self.log("  " + u)

    def on_download(self, event):
        if not self._links:
            wx.MessageBox("请先点击“扫描链接”", "提示",
                          wx.OK | wx.ICON_WARNING)
            return
        save_dir = self.dir_picker.GetPath()
        if not save_dir:
            wx.MessageBox("请选择保存目录", "提示", wx.OK | wx.ICON_WARNING)
            return
        urls = list(self._links)
        self._run_async(lambda: self._download_worker(urls, save_dir))

    def _download_worker(self, urls, save_dir):
        os.makedirs(save_dir, exist_ok=True)
        self.log(f"开始下载到: {save_dir}")

        def progress(done, total):
            pct = int(done * 100 / total) if total else 0
            self._ui(self.gauge.SetValue, pct)
            self._ui(self.SetStatusText, f"下载中 {done}/{total}")

        ok, failed = download_many(urls, save_dir,
                                   progress=progress, log=self.log)
        self.log(f"完成: 成功 {len(ok)}，失败 {len(failed)}")
        for url, err in failed:
            self.log(f"  失败: {url} ({err})")

    def on_organize(self, event):
        base = self.dir_picker.GetPath()
        if not base or not os.path.isdir(base):
            wx.MessageBox("请选择有效的目录", "提示",
                          wx.OK | wx.ICON_WARNING)
            return
        self._run_async(lambda: self._organize_worker(base))

    def _organize_worker(self, base):
        self.log(f"开始归档: {base}（类别: {', '.join(ARCHIVE_KINDS)}）")
        try:
            res = organize_pdfs(base, log=self.log)
        except Exception as e:
            self.log(f"[失败] {e}")
            return
        self.log(f"归档完成：移动 {res['moved']}，跳过 {res['skipped']}")