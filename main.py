import datetime, time, re, pytz, requests,  sys, os, io, ast,textwrap	# Standard Python Libraries - Functions
import pprint, json, logging, requests							# Standard Python Libraries - IO

import sqlite3				# SQLITE database module
import praw					# Reddit API wrapper
import tweepy				# Twitter Reading Module   - tweet object: 
							# https://gist.github.com/dev-techmoe/ef676cdd03ac47ac503e856282077bf2
from PIL import Image 		# Image to Text libraries
import PIL.ImageOps
import pytesseract

class AHL:
	''' The class is a container for the different helper functions. Information is stored
			in a sqlite database rather than in python classes as that was  unnecessary. 
	'''
	def __init__(self, database=None):
		if database != None:
			AHL.database = database
			self.connect_to_database()
			self.update_schedule()
			self.close_database()

	# Helper functions to connect to and disconnect from the database. Should be called at start
	#	and at the end of the program. 
	def connect_to_database(self):
		if AHL.database != None:
			self.db_conn = sqlite3.connect("AHL.sqlite")
		return self.db_conn if self.db_conn != None else False
	def close_database(self):
		if self.db_conn != None:
			self.db_conn.close()
			return True
		return False
	
	# 	
	def __add_games_to_database(self,ics_text, season_ID, team_id):
		''' Returns None if no ICS is empty (season invalid), 
					False if no new games are added
					True if some new games are added

			Searches the provided ICS file for pertenant schedule information. 
			Current Compatable Teams: 
				1. Toronto Marlies
				2. 
			I'm not sure it'll ever be compatable with all teams as there is different information 
			in each team's ICS file. May need to move to an online table reader if expanding to 
			all teams is not possible through simple ICS parsing.
		'''
		c = self.db_conn.cursor()
		schedule_updated = False
		# Regex Expressions for finding game information
		IDs = re.findall("([0-9]{7})@", ics_text)			# IDs for games
		datetimes = re.findall("DTSTART:(.+)", ics_text)	# Datestrings of games
		locations = re.findall("LOCATION:(.+)", ics_text)	# Location of the games
		summaries = re.findall("SUMMARY:(.+)", ics_text)	# Game Summary (Away team @ home team)						
		status = re.findall("STATUS:(.+)", ics_text)		# Game Summary (Away team @ home team)					


		# Yes, I know this isn't pythonic, but for i,j,k,l,m in ID,datetime...doesnt look pythonic either.
		# 		Try and insert the game data into the schedule database, if not possible, game exists already.
		for i in range(len(IDs)):
			away_team = summaries[i].split(" @ ")[0]
			home_team = summaries[i].split(" @ ")[1]
			UTC_start = datetime.datetime.strptime(datetimes[i], "%Y%m%dT%H%M%SZ").replace(tzinfo=pytz.utc)
			try:
				c.execute('''INSERT INTO GameSchedule (
					game_ID, season_ID, game_DateTime,	home_team, away_team, location,		status
					)VALUES (?,?,?,?,?,?,?)''',(
					IDs[i],  season_ID, UTC_start,		home_team, away_team, locations[i], status[i]
					)
				)
				schedule_updated = True
			except sqlite3.IntegrityError as e:
				print("Can't insert game into database as game already exists.")

		self.db_conn.commit()
		return None if IDs == [] else schedule_updated

	def set_game_status(self,game_id,status):
		c = self.db_conn.cursor()
		now = datetime.datetime.today().strftime('%Y-%m-%d %H:%M:%S')
		tomorrow = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
		c.execute(("UPDATE GameSchedule SET status = '"'{0}'"' WHERE game_id = {1}").format(status,game_id))

	def update_schedule(self):
		''' Attempts to update the AHL schedule database through downloading and parsing ICS files
			 to an sqlite database.
		'''
		# temporary starter values to simply update the Toronto Marlies.
		season_id = 65  		# 2019-20 season. +1 each playoff
		team_id = 335				# Toronto Marlies ID
		
		any_update = False
		ICS_update = False
		while ICS_update != None:
			schedule = requests.get(f"http://cluster.leaguestat.com/components/calendar/ical_add_games.php?client_code=ahl&season_id={season_id}&team_id={team_id}").text
			ICS_update = self.__add_games_to_database(schedule, season_id, team_id)
			season_id += 1
			if ICS_update == True:
				any_update = True
			# print(f"Still looping {ICS_update}, {season_id-1}", {schedule})
		return any_update

	def is_gameday(self, team=None):
		c = self.db_conn.cursor()
		now = datetime.datetime.today().strftime('%Y-%m-%d %H:%M:%S')
		tomorrow = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
		c.execute("SELECT * FROM 'GameSchedule' \
			WHERE status = 'CONFIRMED' \
			AND DATETIME(game_DateTime) > datetime(?)",(now,))
		
		# c.execute(f"SELECT * FROM 'GameSchedule' WHERE (DATE(game_DateTime) = {today} AND (home_team = {team} OR away_team = {team}) ")
		game_data = c.fetchone()

		return None if game_data is None else game_data

	def get_last_lineup(self, team=None):
		c = self.db_conn.cursor()
		c.execute(("SELECT * FROM 'Lineups' WHERE ID = (SELECT MAX(game_ID) from 'Lineup') AND team = {0}").format(team))
		return (c.fetchone())
	def store_lineup(self, game_ID, team, Playerslist):
		c = self.db_conn.cursor()
		print(Playerslist)
		json_playerlist = json.dumps(Playerslist) # apparentyl this motherfucker doesn't like single quotes, HOLY SHIT
		print(json_playerlist)
		try:
			c.execute('''INSERT INTO 'Lineups' (game_ID, team, lineup)VALUES (?,?,?)''',(
										 game_ID, team, json_playerlist))		
		except sqlite3.IntegrityError as e:
			print("HEYO! THAT LINEUP ALREADY EXISTS!") 
		self.db_conn.commit()
		return

# Helper Functions
def load_json(file):
	''' just opens and returns json file. Saves a couple lines if used often. '''
	with open(file, 'r') as f:
		return json.load(f)
def build_reddit_table(headers, values):
	'''Builds a string from header & value arrays that is interpretted by reddit as a table.
	'''
	divisor_text = "" 	
	header_text = ""
	value_text = ""

	for header in headers:
		header_text += f"{header}|"
		divisor_text += "--|"

	while values != []:
		for header in headers:
			value_text+= f"{values[0]}|"
			values.remove(values[0])
		value_text += "\n"

	return f"{header_text}\n{divisor_text}\n{value_text}"

def configure_logging(Logging_Level):
	''' Configure the logging module. 
			BasicConfig is used to include logger handlers from other modules. 
	'''

	# creates file/console handlers. file should be always set to DEBUG.
	file_handler = logging.FileHandler('logfile.log',mode='w')
	file_handler.setLevel(logging.DEBUG)
	file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)40s - %(levelname)8s - %(message)s'))
	console_handler = logging.StreamHandler()
	console_handler.setLevel(logging.getLevelName(Logging_Level))  # set console logging level from config

	### Put custom level alterations for other modules here:
	logging.getLogger("prawcore").setLevel(logging.ERROR)  

	# Configure logging using the handlers. 
	logging.basicConfig(
		handlers=[file_handler,console_handler],
		level = logging.DEBUG,
		format='%(asctime)s - %(name)17s  - %(levelname)8s - %(message)s',
		datefmt = '%Y-%m-%d %H:%M:%S'
		)

	return

# Procedural functions to clean up the code
def get_lineup_from_twitter():
	''' Retrieves the player lineup from the Toronto Marlies twitter account that posts
			pictures of the lineup.
	'''
	# Connect to twitter
	twitter_keys = load_json("keys.json")['twitter_keys'] 
	MB_twitter_auth = tweepy.OAuthHandler(twitter_keys['consumer_key'], twitter_keys['consumer_secret'])
	MB_twitter_auth.set_access_token(twitter_keys['access_token'], twitter_keys['access_secret'])
	MB_twitter_connection = tweepy.API(MB_twitter_auth)

	# Grab several tweets.
	PlayerList = []
	tweets = MB_twitter_connection.user_timeline(screen_name = "TorontoMarlies", count = 150)
	#####################   @TorontoMarlies Image Option
	# Look for a tweet that is talks about a lineup and has an image. 
	for tweet in tweets:
		if ("lineup" in tweet.text) and ('media' in tweet.entities):
			image_url = tweet.entities['media'][0]['media_url']
			image_data = requests.get(image_url).content

			# Get player names from image
			pytesseract.pytesseract.tesseract_cmd = r'C:/Program Files/Tesseract-OCR/tesseract.exe'
			image = Image.open(io.BytesIO(image_data))
			image = PIL.ImageOps.invert(image)
			image_text = pytesseract.image_to_string(image).title()

			# Group players into their positional groups
			player_groups = image_text.split("\n\n")
			forwards = re.findall("([a-zA-Z]{2,} [a-zA-Z]{2,})",player_groups[0])
			defenders = re.findall("([a-zA-Z]{2,} [a-zA-Z]{2,})", player_groups[1])
			goalies = re.findall("([a-zA-Z]{2,} [a-zA-Z]{2,})",player_groups[2] )
			Playerslist = [forwards,defenders, goalies]
			break

	return Playerslist
def convert_lineup_to_text(Playerslist):
	'''Helper function to make the program more readable. Takes the playerlist, builds some tables
		and outputs the selftext for the final reddit post. 
	'''	
	forwards = Playerslist[0]
	defenders = Playerslist[1]
	goalies = Playerslist[2]

	forwards_text = build_reddit_table(["LW","C","RW"], forwards)
	defenders_text = build_reddit_table(["LD","RD"],defenders)
	goalie_text = build_reddit_table("G",goalies)

	pretext = textwrap.dedent("""\
	Official Stream: [AHL TV](https://www.watchtheahl.com)

	Stream2: [OnHockey](http://onhockey.tv/)

	TV: NA

	[Marlies Live Radio](http://marlies.ca/listen-live)

	Away Live Radio: NA (WIP)
	___
	""")

	#If you insert the tables with the pretext, the inserted variables don't have a common leading whitespace for dedent to remove.
	return f"{pretext} \n{forwards_text} \n{defenders_text} \n{goalie_text}" 
	 
	
def init(): 
	''' Setup for the execution of the main script closer to gametime.  
	'''
	keys = load_json("keys.json")
	config = load_json("config.json")
	configure_logging(config['Logging_Level'])

	# Connect to the AHL database (not TheAHL.com)
	AHL_Hockey = AHL('AHL.sqlite')
	AHL_Hockey.connect_to_database()


	# If there isn't a game today then quit, otherwise sleep unti lan hour before.
	new_game = AHL_Hockey.is_gameday()
	if new_game == None:
		sys.exit()
	else:
		currentTime = datetime.datetime.now()
		# Sleep until 1 hour before the game. The 2nd indixes is the gametime column. 
		# sleepTime = (datetime.datetime.strptime(new_game[2],'%Y-%m-%d %H:%M:%S+00:00')-currentTime).total_seconds()- 3600 
		# time.sleep(sleepTime)

	print("Executing Main")
	main(AHL_Hockey, new_game)

def main(AHL_Hockey, new_game):
	''' Its gametime! Watch for lineups on twitter and post them to reddit. 
	'''

	# Poll twitter until a lineup is found. If too close to gametime use the last lineup available.
	Playerslist = []
	while Playerslist == []:
		Playerslist = get_lineup_from_twitter()
		time_to_game = (datetime.datetime.strptime(new_game[2],'%Y-%m-%d %H:%M:%S+00:00') - datetime.datetime.now()).total_seconds()
		if (time_to_game < 300) and (Playerslist == []):
			Playerslist = AHL_Hockey.get_last_lineup(team = "Toronto Marlies")
			Playerslist = json.loads(Playerslist)
		else:
			# time.sleep(300)
			pass
	AHL_Hockey.store_lineup(int(new_game[0]),"Toronto Marlies",Playerslist)
	AHL_Hockey.set_game_status(new_game[0],"IN PROGRESS")

	# Build title and selftext for reddit post
	selftext = convert_lineup_to_text(Playerslist)

	# to ensure it gives the right local date I convert the UTC to local gametime.
	UTC_start = datetime.datetime.strptime(new_game[2], "%Y-%m-%d %H:%M:%S+00:00").replace(tzinfo=pytz.utc)
	EST_game_time = UTC_start.astimezone(pytz.timezone('US/Eastern'))

	if new_game[3] == "Toronto Marlies":
		post_title = f"GDT: Toronto Marlies vs. {new_game[4]} - {datetime.datetime.strftime(EST_game_time,'%h %m %p')}"
	else:
		post_title = f"GDT: Toronto Marlies @ {new_game[3]} - {datetime.datetime.strftime(EST_game_time,'%h %m %p')}"


	# Post the new Game Day Thread (GDT) to the sub
	reddit_keys = load_json("keys.json")['reddit_keys'] 
	MB_reddit = praw.Reddit(client_id		= reddit_keys['client_id'], 
							client_secret 	= reddit_keys['client_secret'], 
							user_agent		= reddit_keys['user_agent'], 
							username		= reddit_keys['username'], 
							password		= reddit_keys['password'])

	print(selftext)


	GDT = MB_reddit.subreddit("MacerV").submit(post_title, selftext = selftext)
	GDT.mod.sticky()
	GDT.mod.suggested_sort(sort='new')

	######## stats module
	# wait 5 hours
	# access game reports
	# assign information to gameids. 
	# 		further processing can be done later. 

	AHL_Hockey.set_game_status(new_game[0],"COMPLETE")



if __name__ == '__main__':
	init()