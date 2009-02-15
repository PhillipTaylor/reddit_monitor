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

#I'm going to have an OK button and a Cancel button
#and I have no idea which way they go around so this
#variable is to prove I thought about the issue even
#if I'm wrong. Also, I probably have bigger problems
#than this.
FLIP_MODE_REVERSE = False

class RedditConfigWindow:

	def __init__(self):

		self.user = None
		self.passwd = None
		self.voff = None
		self.hoff = None
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

		#list of tuples made up of (label, default value, mask_characters, bind to variable)
		##CHANGE THE DEFAULT VALUES HERE. NOTE THEY ARE STRINGS SO KEEP THE QUOTES AROUND THEM.
		self.settings = [
				("Reddit Username:",          '',    False),
				("Reddit Password:",          '',    True ),
				("Check Interval (minutes):", '10', False),
		]

		table = gtk.Table(rows=6, columns=2, homogeneous=False)
		self.window.add(table)

		for (row, (label, default_value, apply_mask)) in enumerate(self.settings):
			
			label_component = gtk.Label(label)
			label_component.set_alignment(0, 0.5)

			text_component = gtk.Entry(max=0)
			text_component.set_text(default_value)
			
			if apply_mask:
				text_component.set_visibility(False)
				text_component.set_invisible_char('*')

			table.attach(label_component, 0, 1, row, row + 1, xpadding=2, ypadding=1)
			table.attach(text_component,  1, 2, row, row + 1, xpadding=2, ypadding=1)

			label_component.show()
			text_component.show()

			self.widgets.append(text_component)

		#Add ok and quit buttons
		ok_btn = gtk.Button(stock=gtk.STOCK_OK)
		ok_btn.connect("clicked", self.on_ok)
		ok_btn.set_flags(gtk.CAN_DEFAULT)
		ok_btn.show()

		close_btn = gtk.Button(stock=gtk.STOCK_CANCEL)
		close_btn.connect("clicked", self.on_cancel)
		close_btn.show()

		if FLIP_MODE_REVERSE:
			table.attach(ok_btn, 0, 1, 5, 6, ypadding=2)
			table.attach(close_btn, 1, 2, 5, 6, ypadding=2)
		else:
			table.attach(close_btn, 0, 1, 5, 6, ypadding=2)
			table.attach(ok_btn, 1, 2, 5, 6, ypadding=2)

		self.window.set_default(ok_btn)
		table.show()

	def show(self):
		self.window.show()
		gtk.main()

	def on_ok(self, widget, callback_data=None):
		self.user = self.widgets[0].get_text()
		self.passwd = self.widgets[1].get_text()
		self.interval = self.widgets[2].get_text()

		self.window.hide()
		gtk.main_quit()

	def on_cancel(self, widget, callback_data=None):
		gtk.main_quit()
		sys.exit(0)

class RedditTrayIcon():

	def __init__(self, reddit_session, interval):

		self.reddit = reddit_session
		self.interval = interval

		#create the tray icon
		self.tray = pytrayicon.TrayIcon('Reddit')
		self.eventbox = gtk.EventBox()
		self.tray.add(self.eventbox)
		self.eventbox.connect("button_press_event", self.on_tray_icon_click)
		self.icon_image = gtk.Image()

		#load the two icons
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

		#For some reason self.check_now doesn't work so I need
		#to create a dirty hack.
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

		if self.reddit.has_new_mail():
			self.icon_image.set_from_pixbuf(self.new_mail_icon)
		else:
			self.icon_image.set_from_pixbuf(self.nothing_icon)

		self.timer = gobject.timeout_add(self.interval, self.on_check_now)
		self.menu.show_all()

		self.checking = False
	
if __name__=='__main__':

	cfg_dlg = RedditConfigWindow()
	cfg_dlg.show()

	username = cfg_dlg.user
	password = cfg_dlg.passwd
	#convert to milliseconds
	interval = int(cfg_dlg.interval) * 60000

	reddit_session = reddit.Reddit()
	reddit_session.login(username, password)

	tray_icon = RedditTrayIcon(reddit_session, interval)
	gtk.main()
