import os, re, datetime, logging, pytz
import requests
import sqlite3



def _build_ics_url():
	'''


	'''


	TEAM_ID = 335				# This stays absolutely constant. Toronto Marlies ID
	BASE_SEASON_ID = 65  		# Goes up for each season, allstar, and playoff set. Inconsistant interyear increases
	PLAYOFFS_START = datetime.datetime.strptime("2020-04-12","%Y-%m-%d")
	
	test_date = datetime.datetime.strptime("2020-04-10","%Y-%m-%d")
	# today = datetime.datetime.now() 

	season_id_modifier = 2 if test_date > PLAYOFFS_START else 0
	SEASON_ID = BASE_SEASON_ID + season_id_modifier

	ics_url = f"http://cluster.leaguestat.com/components/calendar/ical_add_games.php?client_code=ahl&season_id={SEASON_ID}&team_id={TEAM_ID}"
	return ics_url

def _add_games_to_database(ics_text):
	db_file = os.path.join(os.path.dirname(__file__), "Schedule.sqlite")
	db_conn = sqlite3.connect(db_file)
	c = db_conn.cursor()
	

	schedule_text = ics_text.split("\n")


	event_data = {}
	ignore_list = {"BEGIN:VCALENDAR","VERSION:2.0","PRODID:","TZID:UTC","DTEND:","DTSTAMP:", "DESCRIPTION:"}
	for line in schedule_text:

		if any(ignore in line for ignore in ignore_list):
			pass
		elif "BEGIN:VEVENT" in line:
			event_data.clear()
		elif "END:VEVENT" in line:
			# print(f"Debug: Event_data: {event_data}")
			# event_data should have UID, DTSTART, LOCATION, SUMMARY, STATUS
			event_data['UID'] = re.search("([0-9]{7})@",event_data['UID']).group(1)


			UTC_start = datetime.datetime.strptime(event_data['DTSTART'], "%Y%m%dT%H%M%SZ").replace(tzinfo=pytz.utc)
			event_data['DTSTART'] = UTC_start.astimezone(pytz.timezone('US/Eastern'))
			teams = event_data['SUMMARY'].split(" @ ") 		# 0 is visitor, 1 is home
			event_data['AWAY_TEAM'] = teams[0]
			event_data['HOME_TEAM'] = teams[1]
			event_data.pop('SUMMARY')
			# event_data['LOCATION'] 	is formatted correctly
			# event_data['STATUS'] 		is formatted correctly

			#print(f"Pushing Dict into SQLITE DB. Dict: {event_data}")
			try:
				c.execute('''INSERT INTO GameSchedule (
					game_ID,game_DateTime,home_team,away_team,location,status)
					VALUES (?,?,?,?,?,?)''', (
					event_data['UID'],
					event_data['DTSTART'],
					event_data['HOME_TEAM'],
					event_data['AWAY_TEAM'],
					event_data['LOCATION'],
					event_data['STATUS']
					)
				)
			except sqlite3.IntegrityError as e:
				print("Can't insert game into database as game already exists.")

			
		else:
			key_and_val = line.split(":")
			event_data[key_and_val[0]] = key_and_val[1]


	db_conn.commit()
	db_conn.close()


def main():
	schedule = requests.get(_build_ics_url()).text
	_add_games_to_database(schedule)

if __name__ == '__main__':
	main()
