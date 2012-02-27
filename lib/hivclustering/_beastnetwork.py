

import datetime, time, random
from math import log
from copy import copy
import hypy as hy
import os
import csv

__all__ = ['edge', 'patient', 'transmission_network', 'parseAEH', 'parseLANL', 'parsePlain']
#-------------------------------------------------------------------------------


def parseAEH (str):
	bits = str.split ('|')
	if len (bits) < 2:
		raise Exception ('Improperly formatted AEH header (need at least "ID|Sample date in mmddyyyy format": %s' % str)
	
	patient_description = {}
	patient_description ['id']   =  bits[0]
	patient_description ['date'] = time.strptime (bits[1],'%m%d%Y')
	patient_description ['rawid'] = str
	
	return patient_description
	
def parseLANL (str):
	bits = str.split ('_')
	if len (bits) < 4:
		raise Exception ('Improperly formatted LANL header (need at least "subtype_country_accession_yyyy": %s' % str)
	
	patient_description = {}
	patient_description ['id']    =  bits[2]
	patient_description ['date']  = time.strptime (bits[3],'%Y')
	patient_description ['rawid'] = str
	
	return patient_description	
	
def parsePlain (str):

	patient_description = {}
	patient_description ['id']    = str
	patient_description ['date']  = None
	patient_description ['rawid'] = str
	
	return patient_description		
	
def tm_to_datetime (tm_object):
	return datetime.datetime (tm_object.tm_year, tm_object.tm_mon, tm_object.tm_mday)


#-------------------------------------------------------------------------------

class edge:
	def __init__ (self, patient1, patient2, date1, date2, visible):
		if patient1 < patient2:
			self.p1    = patient1
			self.p2    = patient2
			self.date1   = date1
			self.date2   = date2
		else:
			self.p2    = patient1
			self.p1    = patient2
			self.date2   = date1
			self.date1   = date2

		if self.p1.id == self.p2.id:
			raise BaseException ("Trying to make an edge between the same patient")
		self.visible = visible

	def compute_direction (self):
		if self.date1 and self.date2:
			if self.p2.edi and self.p2.edi > self.date1:
				return self.p1
			elif self.p1.edi and self.p1.edi > self.date2:
				return self.p2
		return None

	def direction(self):
		dir = self.compute_direction()
		if dir and self.p1 == dir:
			return ['"%s" -> "%s"' % (self.p1.id, self.p2.id), 'normal']
		elif dir and self.p2 == dir:
			return ['"%s" -> "%s"' % (self.p2.id, self.p1.id), 'normal']
			
		return ['"%s" -> "%s"' % (self.p1.id, self.p2.id), 'none']
		
	def chrono_length_days (self):
		if self.date1 and self.date2:
			return abs(tm_to_datetime (self.date1) - tm_to_datetime (self.date2))
		return None
		
	def label (self):
		'''if self.date1 and self.date2:
			diff = self.chrono_length_days()
			return str (diff.days/7)'''
		return ''

	def __hash__ (self):
		return self.p1.__hash__() + self.p2.__hash__()
		
	def __comp__ (self,other):
		if self.p1 == other.p1 and self.p2 == other.p2:
			return 0
		if self.p1 < other.p1:
			return -1
		elif self.p1 > other.p1:
			return 1
		elif self.p2 < other.p2:
			return -1
		return 1
		
	def check_date (self, year, newer = False):
		if newer:
			return (self.date1 == None or self.date1.tm_year >= year) and (self.date2 == None or self.date2.tm_year >= year) 		
		else:
			return (self.date1 == None or self.date1.tm_year <= year) and (self.date2 == None or self.date2.tm_year <= year) 
		
	def __lt__ (self, other):
		return self.__comp__ (other) == -1

	def __le__ (self, other):
		return self.__comp__ (other) <= 0

	def __gt__ (self, other):
		return self.__comp__ (other) == 1

	def __ge__ (self, other):
		return self.__comp__ (other) >= 0
	
	def __ne__ (self, other):
		return not self.__eq__ (other)
		
	def __eq__ (self,other):
		return self.p1 == other.p1 and self.p2 == other.p2
		
	def __repr__ (self):
		return "%s (%s) -- %s (%s)" % (self.p1.id, time.strftime ("%m-%d-%y",self.date1) if self.date1 != None else 'None', self.p2.id, time.strftime ("%m-%d-%y",self.date2) if self.date2 != None else 'None')

#-------------------------------------------------------------------------------


#-------------------------------------------------------------------------------

class patient: 	

	def __init__ (self, id):
		self.id    			= id # a unique patient ID
		self.dates 			= [] # date objects
		self.edi   			= None # estimated date of infection
		self.treatment_date = None # the date treatment started
		self.vl				= None # viral load at baseline
		self.degree			= 0
		self.cluster_id		= None
		self.naive			= None
	
	def __hash__ (self):
		return self.id.__hash__()
		
	def __comp__ (self,other):
		if self.id == other.id:
			return 0
		if self.id < other.id:
			return -1
		return 1

	def __eq__ (self,other):
		return self.id == other.id
		
	def __str__ (self):
		return "Patient %s (degree = %d, dates = %d, cluster_id = %s)" % (self.id, self.degree, len (self.dates), self.cluster_id)
		
	def __lt__ (self, other):
		return self.__comp__ (other) == -1

	def __le__ (self, other):
		return self.__comp__ (other) <= 0

	def __gt__ (self, other):
		return self.__comp__ (other) == 1

	def __ge__ (self, other):
		return self.__comp__ (other) >= 0
	
	def __ne__ (self, other):
		return not self.__eq__ (other)

	def __repr__ (self):
		return self.__str__()
		
	def add_date (self, date):
		if date not in self.dates:
			self.dates.append (date)
		
	def add_degree (self):
		self.degree += 1

	def add_edi  (self, edi):
		self.edi = edi

	def add_treatment  (self, drugz):
		self.treatment_date = drugz
		
	def add_vl (self, vl):
		self.vl = vl
		
	def add_naive (self, naive):
		self.naive = naive
		
	def get_baseline_date (self):
		return min ([k.tm_year for k in self.dates])
		
	def get_length_of_followup (self):
		d1 = tm_to_datetime (self.dates[0])
		if len (self.dates) > 1:
			self.dates.sort()
			d2 = tm_to_datetime(self.dates[-1])
			return d2 - d1
		return d1 - d1
		
	def get_treatment_since_edi (self):
		if self.treatment_date != None and self.edi != None and self.treatment_date >= self.edi:
			d1 = tm_to_datetime (self.treatment_date)
			d2 = tm_to_datetime (self.edi)
			return d1-d2
		return None
		
	def get_dot_string (self, year_vis = None):
	
		'''if self.id [0:4] == '0501':
			lab = self.id [4:]
		else:
			lab = self.id
			
		return '"%s" [label = "%s"];\n' % (self.id, lab) '''
	
		shape = 'ellipse' 
		color = 'white'
		label = str(self.vl) if self.vl != None else ""
		
		edi_info = self.get_treatment_since_edi()
		
		
		if edi_info:
			if edi_info.days <= 30: 
				color = 'green'
			else:
				color = 'yellow'
			#label = str(edi_info.days/7)
		
		if self.naive:
			color = 'red'
			
		if year_vis is not None:
			if self.get_baseline_date () > year_vis:
				return '"%s" [label = "%s", fillcolor = "%s", shape = %s, style = "invis"];\n' % (self.id, label , color, shape)
			
		return '"%s" [label = "%s", fillcolor = "%s", shape = %s];\n' % (self.id, label , color, shape)
			
#-------------------------------------------------------------------------------

class transmission_network:
	
	def __init__ (self):
		self.nodes     = {}
		self.edges     = {} 
		self.adjacency_list = None
		self.sequence_ids = {} # this will store unique sequence ids keyed by edge information (pid and date)
		
	def read_from_csv_file (self,file_name, formatter = None, distance_cut = None):
		if formatter is None:
			formatter = parseAEH
		edgeReader = csv.reader(file_name)
		header = next(edgeReader)
		if len (header) != 3:
			raise IOError ('transmission_network.read_from_csv_file() : Expected a .csv file with 3 columns as input')
		for line in edgeReader:
			distance = float(line[2])
			if distance_cut is not None and distance > distance_cut:
				continue
			self.add_an_edge(line[0],line[1],distance,formatter)	
	
	def insert_patient (self, id, date, add_degree):
		pat = patient (id)
		if pat not in self.nodes:
			self.nodes[pat] = pat
		
		pat = self.nodes[pat]
		pat.add_date  (date)
		if add_degree:
			pat.add_degree()
			
		return pat
		
	def make_sequence_key (self, id, date):
		if date != None:
			return "-".join((id,time.strftime ("%m-%d-%Y",date)))
		return id
		
	def add_an_edge (self, id1, id2, distance, header_parser = None):		
		if header_parser == None:
			header_parser = parseAEH
			
		patient1 = header_parser (id1)
		patient2 = header_parser (id2)
		same = patient1['id'] == patient2['id']
		
		p1 = self.insert_patient (patient1['id'],patient1['date'], not same)
		p2 = self.insert_patient (patient2['id'],patient2['date'], not same)
		
		pid1 = self.make_sequence_key (patient1['id'],patient1['date'])
		if pid1 not in self.sequence_ids:
			self.sequence_ids [pid1] = patient1["rawid"]
		pid2 = self.make_sequence_key (patient2['id'],patient2['date'])
		if pid2 not in self.sequence_ids:
			self.sequence_ids [pid2] = patient2["rawid"]
		
		if not same:
			new_edge = edge (p1,p2,patient1['date'],patient2['date'],True)

			#if abs (new_edge.date1.tm_year - new_edge.date2.tm_year) > 5:
			#	print new_edge
			
			if new_edge not in self.edges:
				self.edges [new_edge] = distance
			else:	
				if distance < self.edges [new_edge]:
					self.edges [new_edge] = distance
				
	def compute_adjacency (self,edges=False):
		self.adjacency_list = {}
		for anEdge in self.edges:
			if anEdge.visible:
				if anEdge.p1 not in self.adjacency_list: self.adjacency_list [anEdge.p1] = [] 	
				if anEdge.p2 not in self.adjacency_list: self.adjacency_list [anEdge.p2] = [] 
				if (edges):
					self.adjacency_list [anEdge.p1].append (anEdge)
					self.adjacency_list [anEdge.p2].append (anEdge)
				else:
					self.adjacency_list [anEdge.p1].append (anEdge.p2)
					self.adjacency_list [anEdge.p2].append (anEdge.p1)
		
	def get_all_treated_within_range (self, daterange, outside = False):
		selection = []
		for node in self.nodes:
			tedi = node.get_treatment_since_edi()
			if tedi and (tedi > daterange if outside else tedi <= daterange):
				selection.append (node)
		return selection

	def get_all_naive (self):
		selection = []
		for node in self.nodes:
			if node.naive:
				selection.append (node)
		return selection
		
	def get_edge_node_count (self):
		vis_nodes = {}
		edges = 0
		
		for edge in self.edges:
			if edge.visible:
				edges += 1
				if edge.p1 not in vis_nodes:
					vis_nodes[edge.p1] = 1
				if edge.p2 not in vis_nodes:
					vis_nodes[edge.p2] = 1
		
		return {'edges': edges, 'nodes': len(vis_nodes)}
				
	def clear_adjacency (self):
		if self.adjacency_list != None:
			del self.adjacency_list
			self.adjacency_list = None	
			for edge in self.edges:
				edge.visible = True

		
	def apply_date_filter	 (self, edge_year, newer = False, do_clear = True):
		if do_clear : self.clear_adjacency()
		for edge in self.edges:
			if edge.visible:
				edge.visible = edge.check_date (edge_year, newer)
			
	def apply_distance_filter (self, distance, do_clear = True):
		if do_clear : self.clear_adjacency()
			
		for edge in self.edges:
			if edge.visible:
				edge.visible = self.edges[edge] <= distance
	
	def apply_id_filter (self, list, strict = False, do_clear = True):
		if do_clear : self.clear_adjacency()
			
		for edge in self.edges:
			if edge.visible:
			    if strict:
				    edge.visible = edge.p1.id in list and edge.p2.id in list			    
			    else:
				    edge.visible = edge.p1.id in list or edge.p2.id in list

	def apply_cluster_filter (self, cluster_ids): # exclude all sequences in a given cluster(s)
		if self.adjacency_list != None:
			for edge in self.edges:
				if edge.p1.cluster_id in cluster_ids or edge.p2.cluster_id in cluster_ids:
					edge.visible = False
					
			del self.adjacency_list
			self.adjacency_list = None
		else:
			raise Exception ("Cannot apply a cluster filter because prior to computing clusters IDs")
			

	def retrieve_clusters (self):
		clusters = {}
		for node in self.nodes:
			#if node.cluster_id == None:
			#	raise BaseException ('Called return_clusters but node %s had no associated cluster ID' % node)
			if node.cluster_id not in clusters:
				clusters [node.cluster_id] = []
			clusters [node.cluster_id].append (node)
		return clusters
			
	
	def clear_filters 		  (self):
		for edge in self.edges:
			edge.visible = True
		
			
	def compute_clusters (self, singletons = False):
		if self.adjacency_list == None:
			self.compute_adjacency ()
			
		clusters = {}
		for aNode in self.nodes:
			aNode.cluster_id = None
			
		cluster_id = [0] # this will pass the object by reference
		
		for node in self.nodes:
			if (singletons or node in self.adjacency_list) and node.cluster_id == None:
				self.breadth_first_traverse (node, cluster_id)
			
	def breadth_first_traverse (self, node, cluster_id):
		if node.cluster_id == None:
			cluster_id [0] += 1
			node.cluster_id = cluster_id [0]
		if node in self.adjacency_list:
			for neighbor_node in self.adjacency_list[node]:
				if neighbor_node.cluster_id == None:
					neighbor_node.cluster_id = node.cluster_id
					self.breadth_first_traverse(neighbor_node, cluster_id)
					
	def generate_csv (self, file):
		file.write ("ID1,ID2,Distance")
		for edge in self.edges:
			if edge.visible:
				file.write("%s,%s,%g\n" % (edge.p1.id, edge.p2.id, self.edges[edge]))	
					
	def write_clusters (self, file):
		file.write ("SequenceID,ClusterID\n")
		for node in self.nodes:
			if node.cluster_id != None:
				file.write ("%s,%d\n" % (self.sequence_ids[self.make_sequence_key (node.id, node.dates[0])],node.cluster_id))
					
				

	def generate_dot (self, file, year_vis = None):
		file.write ('digraph G { overlap="voronoi";\n outputorder = edgesfirst;\nnode[style=filled];\n');
		nodes_drawn = {}
		
		directed = {'undirected':0, 'directed':0}
		
		for edge in self.edges:
			if edge.visible:
				distance = self.edges[edge]
				
				if edge.p1 not in nodes_drawn:
					nodes_drawn[edge.p1] = edge.p1.get_baseline_date()
					file.write (edge.p1.get_dot_string(year_vis))
				if edge.p2 not in nodes_drawn:
					nodes_drawn[edge.p2] = edge.p2.get_baseline_date()
					file.write (edge.p2.get_dot_string(year_vis))
				
				year_diff = abs(edge.date1.tm_year - edge.date2.tm_year)
				if isinstance(edge.compute_direction(),type(None)):
					directed ['undirected'] += 1
				else:
					directed ['directed'] += 1
				edge_attr = edge.direction()
				
				if year_vis is not None:
					if edge.check_date (year_vis) == False:
						file.write ('%s [style="invis" arrowhead = "%s"];\n' % (edge_attr[0], edge_attr[1]));
						continue
						
					
				file.write ('%s [style="bold" label = "%s" arrowhead = "%s"];\n' % (edge_attr[0], edge.label(), edge_attr[1]));

		file.write ("\n};")
		return directed

	def spool_pairwise_distances (self,file):
		for node in self.nodes:
			a_row = []
			for node2 in self.nodes:
				if node != node2:
					an_edge = edge (node, node2, None, None, True)
					
					if an_edge in self.edges:
						a_row.append (str(self.edges[an_edge]))
					else:
						print ("%s %s not an edge" % (node, node2))
						a_row.append ('100.0')
				else:
					a_row.append ('0.0')
					
			#print a_row
			file.write ('\t'.join (a_row))
			file.write ('\n')

	def get_node_degree_list (self, year_cap = None):
		degree_list = {}
		for node in self.nodes:
			if year_cap is not None and node.get_baseline_date() > year_cap:
					degree_list[node.id] = None
			else:
				if node in self.adjacency_list:
					degree_list[node.id] = len (self.adjacency_list[node])	
				else:
					degree_list[node.id] = 0
				
		return degree_list
		
	def sample_subset	(self, size):
		return random.sample (self.nodes, int (size))
		
	def output_sequence_names (self):
		pass
		

	def fit_degree_distribution (self):
		hy_instance = hy.HyphyInterface ();
		script_path = os.path.realpath(__file__)
		hbl_path =  os.path.join(os.path.dirname(script_path), "data", "HBL", "DegreeDistributions.bf")
		all_deg = self.get_degree_distribution()
		hy_instance.queuevar ('allDegs', all_deg)
		hy_instance.runqueue (batchfile = hbl_path)
		bestDistro = hy_instance.getvar ('BestDistro',hy.HyphyInterface.STRING)
		rho = {}
		bic = {}
		p = {}
		for name in ('Waring', 'Yule', 'Pareto', 'Negative Binomial'):
			try:
				rho[name] = hy_instance.getvar (name,hy.HyphyInterface.NUMBER)
			except:
				rho[name] = None
			try:
				bic[name] = hy_instance.getvar (name + "_BIC",hy.HyphyInterface.NUMBER)
			except:
				bic[name] = None
			try:
				p[name] = hy_instance.getvar (name + "_p",hy.HyphyInterface.NUMBER)
			except:
				p[name] = None
		return {'Best' : bestDistro, 'rho': rho, 'BIC' : bic, 'p' : p}


		
	def get_degree_distribution (self, **kwargs):

		degree_distribution = []
		
		subset = None
		if 'subset' in kwargs:
			subset = kwargs ['subset']
			
		directed = False	
		if 'directed' in kwargs:
			directed = bool (kwargs ['directed'])
			
		per_year_fu = None
		if 'peryear' in kwargs:
			per_year_fu = int (kwargs ['peryear'])
			
		per_node	= None
		if 'storenodes' in kwargs:
			per_node = kwargs['storenodes']
			
		if self.adjacency_list == None or (directed and isinstance(self.adjacency_list[list(self.adjacency_list.keys())[0]][0],patient)) or (not directed and isinstance(self.adjacency_list[list(self.adjacency_list.keys())[0]][0],edge)):
			#print 'Redo'
			self.compute_adjacency(directed)
			
		max_diff	= None
		if 'max_diff' in kwargs and 'directed':
			if isinstance (kwargs['max_diff'], int):
				max_diff = datetime.timedelta (days = int (kwargs['max_diff']))

		for node in self.adjacency_list:
			if subset and node not in subset:
				continue
				
			if directed:
				this_degree = 0
				for an_edge in self.adjacency_list[node]:
					dir = an_edge.compute_direction()
					if isinstance(dir,type(None)) or dir == node:
						if max_diff:
							diff = an_edge.chrono_length_days()
							if diff == None or diff <= max_diff:
								this_degree += 1
						else:
							this_degree += 1
			else:
				this_degree = len (self.adjacency_list[node])
				
			if per_year_fu:	
				degree_distribution.append (this_degree/float(per_year_fu - node.get_baseline_date () + 1))
			else:
				if len (degree_distribution) < this_degree + 1:
					for k in range (len (degree_distribution), this_degree+1):
						degree_distribution.append (0)
				degree_distribution[this_degree] += 1
				
			if per_node is not None:
				per_node [node] = this_degree

		#print "Degree : %s " % str (degree_distribution)
			
		if 'transform' in kwargs and not per_year_fu:
			if kwargs['transform'] == 'NetworkStat':
				deg = 0
				for i,d in enumerate(degree_distribution):
					deg += (i+1)*d
				
				return deg
			
			normalizer = 1./sum (degree_distribution)
			degree_distribution = [k * normalizer for k in degree_distribution]

			if kwargs['transform'] == 'CDF' or kwargs['transform'] == 'LogCDF':
				cdf = copy(degree_distribution)
				for k in range (1, len (degree_distribution)):
					cdf[k] += cdf[k-1]
				degree_distribution = [cdf[k] - degree_distribution[k] for k in range (len (degree_distribution))]
				if kwargs['transform'] == 'LogCDF':
					return [log (1-k) for k in degree_distribution [1:]]
				
		if subset:
			if per_year_fu:
				for k in range (len (subset) - len (degree_distribution)):
					degree_distribution.append (0.0)
			else:
				degree_distribution[0] += len (subset) - sum (degree_distribution)
			return degree_distribution
			
		return degree_distribution [1:]