#!/usr/bin/env python
#Reddit.py, a python lib capable of telling determining if you have a new reddit message.
#Written by Phillip (Philluminati) Taylor. Mail to: Phillip.Taylor@bcs.org.uk
#Licensed under the GNU General Public License version 3. Copies of the license can be found online.

import urllib
import urllib2
import os.path
import getopt
import getpass
import sys
import re

REDDIT_USER_AGENT = { 'User-agent': 'Mozilla/4.0 (compatible; MSIE5.5; Windows NT' }
REDDIT_LOGIN_URL = 'http://www.reddit.com/api/login'
REDDIT_PROFILE_PAGE = 'http://www.reddit.com/user/%s/'

#Notes:
#1. Could have better exception handling (i.e. some for 404, wrong password, other basic things)
#2. Could possibly save cookie and reuse it later (no password question on load).
#3. Known bug. If you write a comment on reddit about the regex's this page users you inadvertantly
#   trick it. (e.g. put /static/mailgrey/png) in a comment and it will wrongly think you have no new
#   mail.

class RedditNotLoggedInException:
	pass

class Reddit:

	def __init__(self):

		#regex to extract karma + comment karma.
		self.karma_re = re.compile('<b>(\d+)</b></li><li>comment karma: &#32;<b>(\d+)</b>')

		#Because the login is an ajax post before we need cookies.
		#That's what made this code annoying to write.
		#This code should work against either cookielib or ClientCookie depending on
		#which ever one you have.
		try:
			import cookielib

			#Were taking references to functions / objects here
			#so later on we don't need to worry about which actual
			#import we used.
			self.Request = urllib2.Request
			self.urlopen = urllib2.urlopen

			cookie_jar = cookielib.LWPCookieJar()
			opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookie_jar))
			urllib2.install_opener(opener)

		except ImportError:
			try:
				import ClientCookie

				self.Request = ClientCookie.Request
				self.urlopen = ClientCookie.urlopen

				cookie_jar = ClientCookie.LWPCookieJar()
				opener = ClientCookie.build_opener(ClientCookie.HTTPCookieProcessor(cookie_jar))

			except ImportError:
				raise ImportError("""This code is dependent on either
						 \'cookielib\' or \'ClientCookie\'
						 #and you have neither.
						""")

		self.logged_in = False
		self.user = None

	def login(self, user, passwd):

		if self.logged_in:
			return

		self.user = user

		params = urllib.urlencode({
			'id' : '#login_login-main',
			'op' : 'login-main',
			'passwd' : passwd,
			'user' : user
		})

		try:
			req = self.Request(REDDIT_LOGIN_URL, params, REDDIT_USER_AGENT)
			self.urlopen(req).read()
		except Exception, e:
			print "F*CK: %s", e.message
			self.logged_in = False
			return False

		self.logged_in = True
		return True

	#if user == None then it tells you your own karma (provided you called login())
	#Returns a tuple (karma, comment_karma)
	def get_karma(self, user=None):

		if user == None and not self.logged_in:
			raise RedditNotLoggedInException('Who is this? You haven\'t logged in')

		if user == None:
			user = self.user

		profile_page_to_fetch = REDDIT_PROFILE_PAGE % user

		try:
			req = self.Request(profile_page_to_fetch, None, REDDIT_USER_AGENT)
			page_contents = self.urlopen(req).read()			

		except Exception, e:
			print "Error is related to reading a profile page: %s", e.message
			raise e

		results = self.karma_re.search(page_contents)
		karma = int(results.group(1))
		comment_karma = int(results.group(2))

		return (karma, comment_karma)


	def has_new_mail(self):

		if not self.logged_in:
			raise RedditNotLoggedInException('YOU ARE NOT LOGGED IN')

		profile_page_to_fetch = REDDIT_PROFILE_PAGE % self.user

		try:
			req = self.Request(profile_page_to_fetch, None, REDDIT_USER_AGENT)
			page_contents = self.urlopen(req).read()			

		except Exception, e:
			print "Error is related to reading a profile page: %s", e.message
			raise e

		if page_contents.find('/static/mailgray.png') == -1:
			if page_contents.find('/static/mail.png') == -1:
				dump = open('.dump','w')
				dump.write(page_contents)
				dump.close()
				raise Exception('Bad page returned')
			else:
				return True
		else:
			return False

def run():

	if len(sys.argv) < 2:
		usage()
		sys.exit(2)

	try:
		(options, arguments) = getopt.getopt(sys.argv[1:], 'm')
	except optget.GetoptError, e:
		print e.message
		usage()
		sys.exit(2)

	if len(arguments) == 0:
		print "Username is mandatory"
		usage()
		sys.exit(2)
	else:
		username = arguments[0]

	Red = Reddit()

	if len(options) > 0: #must be the mail check option (because it's the only option)
		passwd = getpass.getpass('Your reddit password please: ')
		Red.login(username, passwd)
		print Red.has_new_mail()
	else:
		(karma, comment_karma) = Red.get_karma(username)
		print 'User %s has %s karma and %s comment karma' % (username, karma, comment_karma)
					

def usage():
	print """Usage: %s -m <reddit-username>\nTo see if you have
		 new mail use -m option. That operation requires a
		 password.""" % sys.argv[0]

if __name__=='__main__':
	run()
