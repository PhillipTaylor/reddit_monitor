#!/usr/bin/env python
import pygtk
pygtk.require('2.0')
import os
import gtk
import gobject
import sys
import time
import subprocess
import webbrowser

import reddit


REDDIT_ICON            = 'icons/reddit.png'
NEW_MAIL_ICON          = 'icons/new_mail.png'
BUSY_ICON              = 'icons/busy.gif'

# If you enter your password here
# it will skip the prompt. However I recommend
# you take advantage of gnome-keyring by leaving
# this alone and following the onscreen advice
DEFAULT_USERNAME       = ''
DEFAULT_PASSWORD       = '' #obvious security flaw if you fill this in.
DEFAULT_CHECK_INTERVAL = 10 #minutes

REDDIT_INBOX_USER_URL  = 'http://www.reddit.com/message/inbox'

class RedditConfigWindow(gtk.Window):

	def __init__(self, features):
		gtk.Window.__init__(self)

		self.user = None
		self.passwd = None
		self.interval = None
		self.features = features

		gtk.Window.__init__(self)
		self.set_title('Reddit Tray Icon Preferences')
		self.set_position(gtk.WIN_POS_CENTER)
		self.set_modal(True)
		self.set_resizable(False)
		self.set_icon_from_file(os.path.abspath(REDDIT_ICON))
		self.connect('delete-event', self.on_cancel)
		
		vbox = gtk.VBox(homogeneous=False, spacing=6)
		vbox.set_border_width(6)

		table = gtk.Table(rows=4, columns=2, homogeneous=False)
		table.set_row_spacings(6)
		table.set_col_spacings(6)

		label_username = gtk.Label('Username:')
		label_username.set_alignment(1, 0.5)
		table.attach(label_username, 0, 1, 0, 1)

		self.text_username = gtk.Entry(max=0)
		self.text_username.set_text(DEFAULT_USERNAME)
		self.text_username.set_activates_default(True)
		table.attach(self.text_username, 1, 2, 0, 1)

		label_password = gtk.Label('Password:')
		label_password.set_alignment(1, 0.5)
		table.attach(label_password, 0, 1, 1, 2)
		
		self.text_password = gtk.Entry(max=0)
		self.text_password.set_text(DEFAULT_PASSWORD)
		self.text_password.set_activates_default(True)
		self.text_password.set_visibility(False)
		self.text_password.set_invisible_char('*')
		table.attach(self.text_password, 1, 2, 1, 2)

		label_interval = gtk.Label('Interval (minutes):')
		label_interval.set_alignment(1, 0.5)
		table.attach(label_interval, 0, 1, 2, 3)

		self.text_interval = gtk.Entry(max=0)
		self.text_interval.set_text(str(DEFAULT_CHECK_INTERVAL))
		self.text_interval.set_activates_default(True)
		table.attach(self.text_interval, 1, 2, 2, 3)
		
		vbox.pack_start(table)
		
		if 'pynotify' in features:
			self.notify = gtk.CheckButton(label='Show notifications')
			self.notify.set_active(True)
			vbox.pack_start(self.notify)
		else:
			self.get_pynotify = gtk.Label('With pynotify you can have pop-up notifications!')
			vbox.pack_start(self.get_pynotify)

		if 'gnome-keyring' in features:
			self.keyring = gtk.CheckButton(label='Save to gnome-keyring and don\'t ask again')
			self.keyring.set_active(True)
			vbox.pack_start(self.keyring)
		else:
			self.get_keyring = gtk.Label('With gnome-keyring you can skip this step securely')
			vbox.pack_start(self.get_keyring)

		bbox = gtk.HButtonBox()
		bbox.set_layout(gtk.BUTTONBOX_END)
		bbox.set_spacing(8)
		
		ok_btn = gtk.Button(stock=gtk.STOCK_OK)
		ok_btn.connect("clicked", self.on_ok)
		ok_btn.set_flags(gtk.CAN_DEFAULT)

		close_btn = gtk.Button(stock=gtk.STOCK_CANCEL)
		close_btn.connect("clicked", self.on_cancel)
		
		bbox.add(close_btn)
		bbox.add(ok_btn)
		vbox.pack_start(bbox)
		self.add(vbox)

		self.set_default(ok_btn)
		self.show_all()
		gtk.main()

	def show(self):
		self.window.show()
		gtk.main()

	def on_ok(self, widget, callback_data=None):
		self.window.hide()
		gtk.main_quit()

	def on_cancel(self, widget, callback_data=None):
		gtk.main_quit()
		sys.exit(0)

	def get_username(self):
		return self.text_username.get_text()

	def get_password(self):
		return self.text_password.get_text()

	def get_interval(self):
		return self.text_interval.get_text()

	def get_notifications(self):
		if 'pynotify' in self.features:
			return self.notify.get_active()
		else:
			return False

	def get_keyring_save(self):
		if 'gnome-keyring' in self.features:
			return self.keyring.get_active()
		else:
			return False

class RedditTrayIcon():

	checking = False
	newmsgs = []

	def __init__(self, features, user, password, interval, pynotify):

		self.reddit = reddit.Reddit()
		self.reddit.login(user, password)
		self.interval = interval
		
		self.pynotify = pynotify
		if 'pynotify' in features:		
			pynotify.init('Reddit')

		self.features = features

		#create the tray icon
		self.tray_icon = gtk.StatusIcon()
		self.tray_icon.connect('activate', self.on_check_now)
		self.tray_icon.connect('popup-menu', self.on_tray_icon_click)

		#load the three icons
		self.reddit_icon = gtk.gdk.pixbuf_new_from_file_at_size(os.path.abspath(REDDIT_ICON), 24, 24)
		self.new_mail_icon = gtk.gdk.pixbuf_new_from_file_at_size(os.path.abspath(NEW_MAIL_ICON), 24, 24)
		self.busy_icon = gtk.gdk.pixbuf_new_from_file_at_size(os.path.abspath(BUSY_ICON), 24, 24)

		self.tray_icon.set_from_pixbuf(self.reddit_icon)

		#create the popup menu
		inbox_now = gtk.MenuItem('_Inbox', True)
		inbox_now.connect('activate', self.on_inbox)
		
		check_now = gtk.MenuItem('_Check Now', True)
		check_now.connect('activate', self.on_check_now)

		reset_now = gtk.MenuItem('_Reset Icon', True)
		reset_now.connect('activate', self.on_reset)

		quit = gtk.MenuItem('_Quit', True)
		quit.connect('activate', self.on_quit)
		
		self.menu = gtk.Menu()
		self.menu.append(inbox_now)
		self.menu.append(check_now)
		self.menu.append(reset_now)
		self.menu.append(quit)
		self.menu.show_all()

		while gtk.events_pending():
			gtk.main_iteration(True)

		self.timer = gobject.timeout_add(self.interval, self.on_check_now)

	def on_tray_icon_click(self, status_icon, button, activate_time):
		self.menu.popup(None, None, None, button, activate_time)
	
	def on_inbox(self, event=None):
		if 'xdg-open' in self.features:
			subprocess.call(['xdg-open', REDDIT_INBOX_USER_URL])
		else:
			webbrowser.open(REDDIT_INBOX_USER_URL)

	def on_reset(self, event=None):
		self.newmsgs = []
		self.tray_icon.set_from_pixbuf(self.reddit_icon)

	def on_quit(self, event=None):
		gtk.main_quit()
		sys.exit(0)

	def on_check_now(self, event=None):

		#poor mans lock
		if self.checking:
			return
		else:
			self.checking = True

		self.tray_icon.set_from_pixbuf(self.busy_icon)
		self.menu.hide_all()

		while gtk.events_pending():
			gtk.main_iteration(True)

		newmsgs = self.reddit.get_new_mail()
		if newmsgs:
			# Add newmsgs at the beginning so the latest message is always at index 0
			self.newmsgs = newmsgs + self.newmsgs

			if 'pynotify' in self.features and self.pynotify != None:
				latestmsg = newmsgs[0]
				title = 'You have a new message on reddit!'
				body  = '<b>%s</b>\n%s' % (latestmsg['subject'], latestmsg['body'])

				balloon = self.pynotify.Notification(title, body)
				balloon.set_timeout(60*1000)
				balloon.set_icon_from_pixbuf(self.reddit_icon)
				balloon.attach_to_status_icon(self.tray_icon)
				balloon.show()

		if self.newmsgs:
			self.tray_icon.set_from_pixbuf(self.new_mail_icon)
			if len(self.newmsgs) == 1:
				self.tray_icon.set_tooltip('1 new message!')
			else:
				self.tray_icon.set_tooltip('%d new messages!' % len(self.newmsgs))
		else:
			self.tray_icon.set_from_pixbuf(self.reddit_icon)
			self.tray_icon.set_tooltip('No new messages.')

		self.menu.show_all()

		self.checking = False

		# Keep timeout alive
		return True

def run():

	#Quick test of our environment.
	#I want to avoid an application that
	#throws ugly messages boxes.

	features = []

	try:
		import pynotify
		features.append('pynotify')
	except ImportError:
		pynotify = None

	#check for xdg-open
	search_path = os.environ.get('PATH').split(':')
	for path in search_path:
		if os.path.exists(os.path.join(path, 'xdg-open')):
			features.append('xdg-open')

	# If they hard code their credentials into the
	# top of this file.
	if DEFAULT_USERNAME != '' and DEFAULT_PASSWORD != '':
		user_details_found = True
		username = DEFAULT_USERNAME
		password = DEFAULT_PASSWORD
		interval = DEFAULT_CHECK_INTERVAL
	else:
		user_details_found = False

	# Can we read the credentials from gnome-keyring?
	if not user_details_found:

		try:
			import gnomekeyring as kr

			features.append('gnome-keyring')

			try:

				matching_cred = kr.find_items_sync(
					kr.ITEM_GENERIC_SECRET,
					{ 'app_ident' : 'reddit_monitor' }
				)

				#stored username and password :-)
				if len(matching_cred) > 0:

					user_details_found = True
					username = matching_cred[0].attributes['username']
					password = matching_cred[0].secret
					interval = int(matching_cred[0].attributes['interval'])

			except kr.NoMatchError:
				pass

		except ImportError:
			pass
	
	if not user_details_found:
		#show dialog

		cfg_dlg = RedditConfigWindow(features)

		username = cfg_dlg.get_username()
		password = cfg_dlg.get_password()
		interval = cfg_dlg.get_interval()

		if not cfg_dlg.get_notifications():
			pynotify = None

		# save password entered to gnome keyring
		if cfg_dlg.get_keyring_save():

			kr.item_create_sync(
				kr.get_default_keyring_sync(),
				kr.ITEM_GENERIC_SECRET,
				'reddit_monitor',
				{
					'app_ident' : 'reddit_monitor',
					'username'  : username,
					'interval'  : str(interval)
				},
				password,
				True
			)

	#show the tray icon
	tray_icon = RedditTrayIcon(
		features,
		username,
		password,
		interval * 60000,
		pynotify
	)

	tray_icon.on_check_now()

	gtk.main()

if __name__=='__main__':
	run()
