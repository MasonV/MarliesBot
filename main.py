import datetime, time, re, sys, logging, os, pytz, requests

import json
import pickle					# custom structure storage module
import sqlite3					# sqlite database module
import pprint					# for printing things prettily

import praw						# Reddit API wrapper
import tweepy					# Twitter Reading Module   - tweet object: 
								# https://gist.github.com/dev-techmoe/ef676cdd03ac47ac503e856282077bf2

from PIL import Image 			# Image to Text libraries
import PIL.ImageOps
import pytesseract



class User:
	'''This is a base user class to store user keys. 
		The more social media platforms that are used, 
		the more worthwhile this class becomes. 
	'''							 
	def __init__(self, platform, *args):
		self.platform = platform

		# Declaration of secrets, tokens, passwords, etc.
		if args is not None:
			for key, val in args[0].items() :				 
				setattr(self, key, val)
class Reddit_User(User):  
	'''This class is used to create an easy means of creating helper
		functions for the PRAW wrapper while maintaining structre.

		Additionally, the R_User/R_Mod specifications makes it 
		easy to remember what kind of commands a particular user
		should have available at their disposal. 
	'''

	# Pass the reddit API keys (name & password needed for posting)
	def __init__(self, reddit_keys):
		super().__init__('Reddit', reddit_keys)
		if all(hasattr(self, arg) for arg in ["username","password"]):  
			self.ReadOnly = False
		else: self.ReadOnly = True

	# Establish a link to reddit through PRAW and return that connection
	def establish_api_connection(self):			
		self.reddit = praw.Reddit(
			client_id=self.client_id, 
			client_secret=self.client_secret,
			user_agent=self.user_agent, 
			username=self.username, 
			password=self.password)
		return self.reddit

	# creates a new reddit post based on provided Kwargs.
	# kwargs - https://praw.readthedocs.io/en/latest/code_overview/models/subreddit.html?highlight=submit#praw.models.Subreddit.submit
	def create_post(self,subreddit, title, **kwargs):
		self.thread = self.reddit.subreddit(subreddit).submit(title, **kwargs)
		return self.thread
class Reddit_Mod(Reddit_User):
	'''Similar to Reddit_User, this class is a subclass meant to make
		available function calls more easy to remember and complete.
		I.E. Only Reddit_mods can sticky posts and comments
	'''

	# Passes the reddit API keys, and inheret the Reddit_User Functions. 
	def __init__(self, reddit_keys):
		super().__init__(reddit_keys)

	# Calls create_post and then sorts/stickies accordingly. 
	def create_sticky_post(self, subreddit, title, 
						   sticky=True, sort='blank',**kwargs):
		self.thread = self.create_post(subreddit, title, **kwargs)
		self.thread.mod.sticky(state=sticky,bottom=False)
		self.thread.mod.suggested_sort(sort=sort)
		return self.thread

class Twitter_User(User):
	#The twitter user has its own connection to allow for seperate connections from different twitter accounts if desired. 
	def __init__(self,twitter_keys):
		super().__init__('Twitter', twitter_keys)


	#Establishes a connect through the tweepy api to twitter
	def establish_api_connection(self):
		self.auth = tweepy.OAuthHandler(self.consumer_key, self.consumer_secret)
		self.auth.set_access_token(self.access_token, self.access_secret)
		self.twitter_api = tweepy.API(self.auth)
		return self.twitter_api

	# returns tweets from target user
	def get_tweets(self,target=None,count=20,since_id=None, max_id=None,page=None):
		return self.twitter_api.user_timeline(
			screen_name=target, count = count, since_id = since_id, max_id = max_id, page = page);

class HockeyGame:
	schedule = None
	def __init__(self, scheduleFile):
		if scheduleFile != None:
			HockeyGame.schedule = scheduleFile
	def is_gameday(self):
		dir = os.path.dirname(os.path.realpath(__file__))
		db_file = os.path.join(dir, HockeyGame.schedule)
		db_conn = sqlite3.connect(db_file)
		

		####update schedule
		# if today > last_game_datetime in db
		#	Call get_Schedule.main	


		c = db_conn.cursor()
		today = datetime.datetime.today().strftime('%Y-%m-%d')
		c.execute("SELECT * FROM 'GameSchedule' WHERE DATE(game_DateTime) = '2019-10-05'")
		# c.execute(f"SELECT * FROM 'GameSchedule' WHERE DATE(game_DateTime) = {today}")
		game_data = c.fetchone()
		db_conn.close()

		if game_data is not None:
			self.game_ID = game_data[0]
			if ":" == game_data[1][-3:-2]:
				game_starttime = game_data[1][:-3]+game_data[1][-2:]

			self.game_datetime = datetime.datetime.strptime(game_starttime,'%Y-%m-%d %H:%M:%S%z')
			self.home_team = game_data[2]
			self.away_team = game_data[3]
			self.location  = game_data[4]
			self.status	= game_data[5]

		return None if game_data is None else True
	def sleep_to_game(self,buffer):
		currentTime = datetime.datetime.now().replace(tzinfo=pytz.timezone('US/Eastern'))
		sleepTime = (self.game_datetime-currentTime).total_seconds()- buffer
		print("Sleep time = " + str(sleepTime)) 
		if sleepTime>0 :
			print("Game is at " + str(self.game_datetime) + ", sleeping for " + str(sleepTime/3600) + " hours.")
			time.sleep(sleepTime)
	def prepare_GDT(self):
		if home_team == "Toronto Marlies":
			self.pretitle = "GDT: " + home_team + " vs " + away_team + d.strftime('%h %m %p')
			self.title = "GDT: " + home_team + " vs " + away_team + " - " + d.strftime('%b %d')
			self.title2 = "Link to " + home_team
		else:
			self.pretitle = "GDT: " + home_team + " vs " + away_team + d.strftime('%b %d %p')
			self.title = "GDT: " + away_team + " vs " + home_team + " - " + d.strftime('%b %d')
			self.title2 = ""
class HockeyPlayer:
	# def __newa__(cls,player_name):
		# if position in ['G','LD','RD','LW','C','RW']
			# return super().__init__(player_name,position)
		# else
			# return RaiseError
	def __init__(self,player_name):
		self.player_name = player_name

def configure_logging():
	'''Configure the logging module. 

		BasicConfig is used to ensure that imports that use logging
		will have their logs piped into the logfile.This is important
		as it means you can see PRAW timeouts, max retries,etc.
	'''

	# creates file/console handlers. file should be always set to DEBUG.
	file_handler = logging.FileHandler('logfile.log',mode='w')
	file_handler.setLevel(logging.DEBUG)
	file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)40s - %(levelname)8s - %(message)s'))
	console_handler = logging.StreamHandler()
	console_handler.setLevel(logging.INFO)

	# Configure logging using the handlers. 
	# WARNING: Level acts as an overall level filter over handlers 
	logging.basicConfig(
		handlers=[file_handler,console_handler],
		level = logging.DEBUG,
		format='%(asctime)s - %(name)17s  - %(levelname)8s - %(message)s',
		datefmt = '%Y-%m-%d %H:%M:%S'
		)
	
	return


def names_from_image(file_image):
	print("converting image to text")
	pytesseract.pytesseract.tesseract_cmd = r'C:/Program Files/Tesseract-OCR/tesseract.exe'
	image = Image.open(file_image)
	inverted_image = PIL.ImageOps.invert(image)
	inverted_image.save('test_inverted.jpg')
	image_text = pytesseract.image_to_string(Image.open('test_inverted.jpg'))
	print(f"Text found: {image_text}.")
	return image_text

def get_lineup(twitter_user):
	PlayerList = []
	target = "TorontoMarlies"
	print("Retreiving tweets from user: " + target)
	tweets = twitter_user.get_tweets(target,150)
	
	#####################   @TorontoMarlies Image Option
	for tweet in tweets:
		if "lineup" in tweet.text:
			print("LINEUP FOUND!")
			if 'media' in tweet.entities:
				for image in  tweet.entities['media']:
					print(f"Found image: {image['media_url']}")

					img_data = requests.get(image['media_url']).content
					with open('lineup.jpg', 'wb') as handler:
						handler.write(img_data)


					image_text = names_from_image('lineup.jpg').title()
					player_groups = image_text.split("\n\n")
					forwards = re.findall("([a-zA-Z]{2,} [a-zA-Z]{2,})",player_groups[0])
					defenders = re.findall("([a-zA-Z]{2,} [a-zA-Z]{2,})", player_groups[1])
					goalies = re.findall("([a-zA-Z]{2,} [a-zA-Z]{2,})",player_groups[2] )
					Playerslist = [forwards,defenders, goalies]
					return Playerslist

	return Playerslist
	
	
def init(): 

	configure_logging()
	TheGame = HockeyGame('Schedule.sqlite')

	if TheGame.is_gameday() == None:
		sys.exit()
	# TheGame.sleep_to_game(3600)
	main(TheGame)



def convert_lineup_to_text(Playerslist)
	
	# MY NAME IS HAMMER! AND YOU ARE A NAIL!!!!!!
	forwards = Playerslist[0]
	defenders = Playerslist[1]
	goalies = Playerslist[2]

	pos = "LW"
	forwards_text = "LW|C|RW\n--|--|--\n"
	for forward in forwards:
		if pos == "LW":
		 	forwards_text+= f"{forward}|"
		 	pos = "C"
		elif pos == "C":
			forwards_text+= f"{forward}|"
			pos = "RW"
		elif pos == "RW":
			forwards_text+= f"{forward}\n"
			pos = "LW"

	is_LD = True 
	defenders_text = "LD|RD\n--|--\n"
	for defender in defenders:
		if is_LD: 	defenders_text+= f"{defender}|"
		else:		defenders_text+= f"{defender}\n"
		is_LD ^= True

	goalie_text = f"Goalie|\n--|--\n{goalies[0]}|\n{goalies[1]}|"

	selftext_header = f"""Official Stream: [AHL TV](https://www.watchtheahl.com)
	Stream2: [OnHockey](onhockey.tv)
	TV: NA
	[Marlies Live Radio](http://marlies.ca/listen-live)
	Away Live Radio: NA (WIP)"""

	selftext = f"{selftext_header}\n{forwards_text}\n{defenders_text}\n{goalie_text}"
	return selftext


def main(hockey_game):
	print("Executing main")

	TIME_TO_GAME = 5 ##maybe load from config
	with open("keys.json", 'r') as f:
		keys = json.load(f)
	reddit_keys = keys['reddit_keys'] 
	twitter_keys = keys['twitter_keys'] 


	MB_t = Twitter_User(twitter_keys)
	MB_t_conn = MB_t.establish_api_connection()	

	MB_r = Reddit_Mod(reddit_keys)
	MB_r_conn = MB_r.establish_api_connection()



	Playerslist = []
	while Playerslist == []:
		Playerslist = get_lineup(MB_t)
		if (TIME_TO_GAME < 300) and (Playerslist == []):
			Playerslist = [
				['Michael Carcone', 'Chris Mueller', 'Jeremy Bracco', 
				'Mason Marchment', 'Adam Brooks', 'Trevor Moore', 
				'Dmytro Timashov', 'Pierre Engvall', 'Egor Korshkov', 
				'Nicholas Baptiste', 'Colin Greening', 'Josh Jooris'],
				 
				 ['Rasmus Sandin', 'Timothy Liljegren', 
				 'Calle Rosen', 'Vincent Loverde', 
				 'Andreas Borgman', 'Jesper Lindgren'], 

				 ['Kasimir Kaskisuo', 'Michael Hutchinson']]
		else:
			# time.sleep(300)
			pass
		#store lineup as [name, gameId, date, position, position rank] #I can join full game stats later.


	selftext = convert_lineup_to_text(Playerslist)

	# post = MB_r.create_sticky_post("TorontoMarlies",title, sticky=True, sort='new')

	######## stats module
	# wait 5 hours
	# access game reports
	# assign information to gameids. 
	# 		further processing can be done later. 

if __name__ == '__main__':
	init()