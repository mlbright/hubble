from .Report import *

# Calculate the number of users that have contributed to more than one
# organization over the last two years
class ReportOrgCollaboration(Report):
	def name(self):
		return "org-collaboration"

	# The data is overwritten every day, so skip reading the old data
	def readData(self):
		pass

	def updateData(self):
		newHeader, newData = self.parseData(
			self.executeQuery(self.query(self.yesterday()))
		)
		collab = {}
		orgs = []

		# Generate a dictionary to easily access the MySQL data
		for row in newData:
			source = row[0]
			target = row[1]
			count = row[2]
			if source not in collab:
				collab[source] = {}
			collab[source][target] = int(count)
			if source not in orgs:
				orgs.append(source)
			if target not in orgs:
				orgs.append(target)

		orgs.sort()
		matrix = [[0 for j in range(len(orgs))] for i in range(len(orgs))]

		# Transform the MySQL data into a matrix using the dictionary
		for sInd, sVal in enumerate(orgs):
			for tInd, tVal in enumerate(orgs):
				if sVal in collab and tVal in collab[sVal]:
					matrix[sInd][tInd] = collab[sVal][tVal]
				else:
					matrix[sInd][tInd] = 0

		self.header = orgs
		self.data = matrix

	# Calculates a table with all "org, pusher" combinations for the given time range
	def pushersToOrgSubquery(self, timeRange):
		query = '''
			SELECT orgs.login as org_name,
			       orgs.id as org_id,
			       pushes.pusher_id
			FROM users AS orgs,
			     repositories,
			     pushes
			WHERE orgs.type = "organization"
			  AND orgs.id = repositories.owner_id
			  AND repositories.id = pushes.repository_id
			  AND cast(pushes.created_at AS DATE) BETWEEN "''' + str(timeRange[0]) + '''" and "''' + str(timeRange[1]) + '''"
			GROUP BY orgs.id,
			         pushes.pusher_id
		'''
		return query

	# Calculate the "home" org of a user based on the number of pushes in given time range
	def homeOrgSubquery(self, timeRange):
		query = '''
			SELECT org_name, org_id, pusher_id, MAX(push_count)
			FROM (
				SELECT orgs.login AS org_name, orgs.id AS org_id, pusher_id, COUNT(*) AS push_count
				FROM users AS orgs, repositories, pushes
				WHERE orgs.type = "organization"
				  AND orgs.id = repositories.owner_id
				  AND repositories.id = pushes.repository_id
				  AND cast(pushes.created_at AS DATE) BETWEEN "''' + str(timeRange[0]) + '''" and "''' + str(timeRange[1]) + '''"
				GROUP BY org_id, pusher_id
			) AS counts
			GROUP BY pusher_id
		'''
		return query

	def query(self, date):
		query = '''
			SELECT source.org_name AS source,
			       target.org_name AS target,
			       COUNT(*) AS org_count
			FROM
				(''' + self.homeOrgSubquery(self.timeRangeTotal()) + ''') AS source
				LEFT JOIN (''' + self.pushersToOrgSubquery(self.timeRangeTotal()) + ''') AS target
					ON source.pusher_id = target.pusher_id
			WHERE source.org_id != target.org_id
			GROUP BY source.org_id,
			         target.org_id
			ORDER BY LOWER(source.org_name)
		'''
		return query