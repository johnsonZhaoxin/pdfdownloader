# -*- coding: utf-8 -*-
import wx

from gui.main_frame import MainFrame


def main():
    app = wx.App(False)
    frame = MainFrame(None, title="PDF批量下载器")
    frame.Show()
    app.MainLoop()


if __name__ == "__main__":
    main()