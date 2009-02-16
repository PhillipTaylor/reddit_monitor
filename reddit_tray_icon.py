#!/usr/bin/env python
import pygtk
pygtk.require('2.0')
import os
import gtk
import gobject
import sys
import time
import pytrayicon

import reddit

NOTHING_HAPPENING_ICON = 'icons/reddit.png'
NEW_MAIL_ICON          = 'icons/new_mail.png'
BUSY_ICON              = 'icons/busy.gif'
DEFAULT_USERNAME       = ''
DEFAULT_PASSWORD       = '' #obvious security flaw if you fill this in.
DEFAULT_CHECK_INTERVAL = 10 #minutes

class RedditConfigWindow:

	def __init__(self):

		self.user = None
		self.passwd = None
		self.interval = None
		self.widgets = []

		self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
		self.window.set_title('Reddit Tray Icon Parameters')
		self.window.set_border_width(5)
		self.window.set_position(gtk.WIN_POS_CENTER)
		self.window.set_modal(True)
		self.window.set_resizable(True)
		icon = gtk.gdk.pixbuf_new_from_file(NOTHING_HAPPENING_ICON)
		gtk.window_set_default_icon_list((icon))

		table = gtk.Table(rows=4, columns=2, homogeneous=False)
		self.window.add(table)

		self.label_username = gtk.Label('Username')
		self.label_username.set_alignment(0, 0.5)
		table.attach(self.label_username, 0, 1, 0, 1, xpadding=2, ypadding=1)
		self.label_username.show()

		self.text_username = gtk.Entry(max=0)
		self.text_username.set_text(DEFAULT_USERNAME)
		table.attach(self.text_username, 1, 2, 0, 1, xpadding=2, ypadding=1)
		self.text_username.show()

		self.label_password = gtk.Label('Password')
		self.label_password.set_alignment(0, 0.5)
		table.attach(self.label_password, 0, 1, 1, 2, xpadding=2, ypadding=1)
		self.label_password.show()
		
		self.text_password = gtk.Entry(max=0)
		self.text_password.set_text(DEFAULT_PASSWORD)
		self.text_password.set_visibility(False)
		self.text_password.set_invisible_char('*')
		table.attach(self.text_password, 1, 2, 1, 2, xpadding=2, ypadding=1)
		self.text_password.show()

		self.label_interval = gtk.Label('Interval (minutes)')
		self.label_interval.set_alignment(0, 0.5)
		table.attach(self.label_interval, 0, 1, 2, 3, xpadding=2, ypadding=1)
		self.label_interval.show()

		self.text_interval = gtk.Entry(max=0)
		self.text_interval.set_text(str(DEFAULT_CHECK_INTERVAL))
		table.attach(self.text_interval, 1, 2, 2, 3, xpadding=2, ypadding=1)
		self.text_interval.show()

		#Add ok and quit buttons
		ok_btn = gtk.Button(stock=gtk.STOCK_OK)
		ok_btn.connect("clicked", self.on_ok)
		ok_btn.set_flags(gtk.CAN_DEFAULT)
		ok_btn.show()

		close_btn = gtk.Button(stock=gtk.STOCK_CANCEL)
		close_btn.connect("clicked", self.on_cancel)
		close_btn.show()

		#Reverse these lines if you think the button order is wrong.
		table.attach(ok_btn, 0, 1, 5, 6, ypadding=2)
		table.attach(close_btn, 1, 2, 5, 6, ypadding=2)

		self.window.set_default(ok_btn)
		table.show()

	def show(self):
		self.window.show()
		gtk.main()

	def on_ok(self, widget, callback_data=None):
		self.window.hide()
		gtk.main_quit()

	def get_username(self):
		return self.text_username.get_text()

	def get_password(self):
		return self.text_password.get_text()

	def get_interval(self):
		return self.text_interval.get_text()

	def on_cancel(self, widget, callback_data=None):
		gtk.main_quit()
		sys.exit(0)

class RedditTrayIcon():

	def __init__(self, user, password, interval):

		self.reddit = reddit.Reddit()
		self.reddit.login(user, password)
		self.interval = interval


		#create the tray icon
		self.tray = pytrayicon.TrayIcon('Reddit')
		self.eventbox = gtk.EventBox()
		self.tray.add(self.eventbox)
		self.eventbox.connect("button_press_event", self.on_tray_icon_click)
		self.icon_image = gtk.Image()

		#load the three icons
		pixbuf = gtk.gdk.pixbuf_new_from_file(os.path.abspath(NOTHING_HAPPENING_ICON))
		scaledbuf = pixbuf.scale_simple(24, 24, gtk.gdk.INTERP_BILINEAR)
		self.nothing_icon = scaledbuf

		pixbuf2 = gtk.gdk.pixbuf_new_from_file(os.path.abspath(NEW_MAIL_ICON))
		scaledbuf2 = pixbuf2.scale_simple(24, 24, gtk.gdk.INTERP_BILINEAR)
		self.new_mail_icon = scaledbuf2

		pixbuf3 = gtk.gdk.pixbuf_new_from_file(os.path.abspath(BUSY_ICON))
		scaledbuf3 = pixbuf3.scale_simple(24, 24, gtk.gdk.INTERP_BILINEAR)
		self.busy_icon = scaledbuf3

		self.icon_image.set_from_pixbuf(self.nothing_icon)
		self.eventbox.add(self.icon_image)
		self.tray.show_all()

		#create the popup menu
		self.check_now = gtk.MenuItem('_Check Now', True)
		self.check_now.connect('activate', self.on_check_now)

		self.reset_now = gtk.MenuItem('_Reset Icon', True)
		self.reset_now.connect('activate', self.on_reset)

		self.quit = gtk.MenuItem('_Quit', True)
		self.quit.connect('activate', self.on_quit)
		
		self.menu = gtk.Menu()
		self.menu.append(self.check_now)
		self.menu.append(self.reset_now)
		self.menu.append(self.quit)
		self.menu.show_all()

		while gtk.events_pending():
			gtk.main_iteration(True)

		self.checking = False

		self.timer = gobject.timeout_add(self.interval, self.on_check_now)

	def on_tray_icon_click(self, signal, event):
		self.menu.popup(None, None, None, event.button, event.time)

	def on_reset(self, event=None):
		self.icon_image.set_from_pixbuf(self.nothing_icon)

	def on_quit(self, event=None):
		gtk.main_quit()
		sys.exit(0)

	def on_check_now(self,event=None):

		#poor mans lock
		if self.checking:
			return
		else:
			self.checking = True

		self.icon_image.set_from_pixbuf(self.busy_icon)
		self.menu.hide_all()
		
		while gtk.events_pending():
			gtk.main_iteration(True)

		if self.reddit.get_new_mail():
			self.icon_image.set_from_pixbuf(self.new_mail_icon)
		else:
			self.icon_image.set_from_pixbuf(self.nothing_icon)

		self.timer = gobject.timeout_add(self.interval, self.on_check_now)
		self.menu.show_all()

		self.checking = False
	
if __name__=='__main__':

	cfg_dlg = RedditConfigWindow()
	cfg_dlg.show()

	tray_icon = RedditTrayIcon(
		cfg_dlg.get_username(),
		cfg_dlg.get_password(),
		int(cfg_dlg.get_interval()) * 60000
	)

	gtk.main()
