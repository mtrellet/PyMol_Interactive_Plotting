import time
import math
import logging

from rdflib.plugins.sparql import prepareQuery
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, XSD

from utils import center_of_mass

logging.basicConfig(filename='pymol_session.log',filemode='w',level=logging.INFO)

class RDF_Handler:
    def __init__(self, ontology, db_file):
        self.rdf_parsed = False
        #self.main_handler = main_handler
        self.rdf_graph = Graph()
        self.parse_rdf(ontology, db_file)


    def parse_rdf(self,ontology,filename):
        """ Parse the RDF database """
        start_time = time.time()

        # Parsing of ontology
        logging.info("Parsing of %s..." % ontology)
        self.rdf_graph.parse(ontology, format="n3")
        logging.info ("---- %s seconds ----" % str(time.time()-start_time))
        logging.info("Number of triples: %d" % len(self.rdf_graph))

        # Parsing of RDF DB
        logging.info("Parsing of %s..." % filename)
        self.rdf_graph.parse(filename, format="n3")
        logging.info ("---- %s seconds ----" % str(time.time()-start_time))
        logging.info("Number of triples: %d" % len(self.rdf_graph))
        self.rdf_parsed = True

    def query_sub_rdf(self, canvas, xlow, xhigh, ylow, yhigh, scale):
        """ Query the RDF graph for specific range of values made by user selection """
        
        query = 'SELECT ?id WHERE { ?point rdf:type my:Point . ?point my:Y_type "'+str(canvas.y_query_type)+'" . ?point my:Y_value ?y . FILTER (?y > '+str(ylow)+' && ?y < '+str(yhigh)+') . ?point my:X_type "'+str(canvas.x_query_type)+'" . ?point my:X_value ?x . FILTER (?x > '+str(xlow)+' && ?x < '+str(xhigh)+') . ?point my:represent ?mod . ?mod my:'+scale.lower()+'_id ?id .}'
        logging.info("QUERY: \n%s" % query)
        q = prepareQuery(query, initNs = { "my": "http://www.semanticweb.org/trellet/ontologies/2015/0/VisualAnalytics#" })
        qres = self.rdf_graph.query(q)

        logging.info("Number of queried entities: %d " % len(qres))

        models = set()
        for row in qres:
            models.add(int(row[0]))

        return models

    def query_rdf(self, x_query_type, y_query_type, scale):
        """ Query the RDF graph to build complete plot """
        
        query = 'SELECT ?x ?y ?id WHERE { ?point rdf:type my:Point . ?point my:Y_type "'+y_query_type+'" . ?point my:Y_value ?y . ?point my:X_type "'+x_query_type+'" . ?point my:X_value ?x . ?point my:represent ?mod . ?mod my:'+scale.lower()+'_id ?id .}'
        logging.info("QUERY: \n%s" % query)
        q = prepareQuery(query, initNs = { "my": "http://www.semanticweb.org/trellet/ontologies/2015/0/VisualAnalytics#" })
        qres= self.rdf_graph.query(q)
        
        logging.info("Number of queried entities: %d " % len(qres))

        return qres

    def get_analyses(self, scale):
    	""" Get which analyses already exist for specific scale """

    	query = 'SELECT DISTINCT ?x_type ?y_type WHERE { ?point my:X_type ?x_type . ?point my:Y_type ?y_type . ?point my:represent ?ind . ?ind rdf:type ?type . ?type rdfs:subClassOf* my:'+scale+' .}'
        logging.info("QUERY: \n%s" % query)
        q = prepareQuery(query, initNs = { "my": "http://www.semanticweb.org/trellet/ontologies/2015/0/VisualAnalytics#" })
        qres = self.rdf_graph.query(q)

        logging.info("Number of queried entities: %d " % len(qres))

        return qres

    def add_distance_points(self, item_selected, model_selected, scale):
    	item_list, indiv_list = self.get_id_indiv_from_RDF(model_selected)

    	if scale == "residue":
            ref_x, ref_y, ref_z = center_of_mass.get_com("resid %s and model %04d" % (str(item_selected), model_selected))
        elif scale == "atom":
            ref_x, ref_y, ref_z = center_of_mass.get_com("id %s and model %04d" % (str(item_selected), model_selected))
        logging.info("Coordinates of reference item: %f %f %f" % (ref_x, ref_y, ref_z))

    	my = Namespace("http://www.semanticweb.org/trellet/ontologies/2015/0/VisualAnalytics#")
        last_point_id = self.get_last_id("point")
        nb_pt = 1
        start_time = time.time()
        for item in item_list:
            if item != item_selected:
                if scale == "residue":
                    x,y,z = center_of_mass.get_com("resid %s and model %04d" % (str(item), model_selected))
                elif scale == "atom":
                    x,y,z = center_of_mass.get_com("id %s and model %04d" % (str(item), model_selected))
                logging.info("Coordinates x y z : %f %f %f " % (x,y,z))
                dist = math.sqrt(math.pow((ref_x-x),2)+math.pow((ref_y-y),2)+math.pow((ref_z-z),2))
                logging.info("Distance: %f" % dist)
                point = URIRef(my+"POINT_"+str(last_point_id+nb_pt))
                self.rdf_graph.add( (point, RDF.type, my.point) )
                self.rdf_graph.add( (point, my.X_value, Literal(item)) )
                self.rdf_graph.add( (point, my.Y_value, Literal(dist)))
                if scale == "residue":
                    self.rdf_graph.add( (point, my.X_type, Literal('resid')))
                    res = URIRef(str(indiv_list[nb_pt]))
                    self.rdf_graph.add( (point, my.represent, res))
                elif scale == "atom":
                    self.rdf_graph.add( (point, my.X_type, Literal('atomid')))
                    at = URIRef(str(indiv_list[nb_pt]))
                    self.rdf_graph.add( (point, my.represent, at))
                self.rdf_graph.add( (point, my.Y_type, Literal('distance')))
                
                nb_pt += 1

        logging.info("---- %s seconds ----" % str(time.time()-start_time))


    def get_id_indiv_from_RDF(self, model):
        query = 'SELECT ?res ?resid WHERE{ ?res my:residue_id ?resid . ?res my:belongs_to+ my:MODEL_'+str(model)+' .} ORDER BY ?resid'
        logging.info("QUERY: \n%s" % query)

        q = prepareQuery(query, initNs = { "my": "http://www.semanticweb.org/trellet/ontologies/2015/0/VisualAnalytics#" })
        qres = self.rdf_graph.query(q)

        logging.info("Number of residues in specified model: %d " % len(qres))

        id_list = []
        indiv_list = []

        for row in qres:
            id_list.append(int(row[1]))
            indiv_list.append(row[0])
            logging.info("indiv: %s / id: %d" % (indiv_list[-1], id_list[-1]))

        return id_list, indiv_list

    def get_last_id(self, type):
        query = 'SELECT ?id WHERE {?id rdf:type my:'+type+' .}'
        logging.debug("QUERY: \n%s" % query)

        q = prepareQuery(query, initNs = { "my": "http://www.semanticweb.org/trellet/ontologies/2015/0/VisualAnalytics#" })
        qres = self.rdf_graph.query(q)

        list_id = []
        import re
        p = re.compile("POINT_(.*)")
        for row in qres:
            tmp = p.search(row[0])
            list_id.append(int(tmp.groups()[0]))

        list_id.sort()
        return list_id[-1]

    def get_mini_maxi_values(self, xtype, ytype, scale):
        """ Get minimum and maximum for x and y values from POINT individuals """

        query = 'SELECT (MIN(?x) AS ?xmin) (MAX(?x) AS ?xmax) (MIN(?y) AS ?ymin) (MAX(?y) AS ?ymax) WHERE { ?point my:X_value ?x . ?point my:Y_value ?y . ?point my:X_type "'+xtype+'" . ?point my:Y_type "'+ytype+'" . ?point my:represent ?ind . ?ind rdf:type ?type . ?type rdfs:subClassOf* my:'+scale+' .}'
        logging.info("QUERY: \n%s" % query)

        q = prepareQuery(query, initNs = { "my": "http://www.semanticweb.org/trellet/ontologies/2015/0/VisualAnalytics#" })
        qres = self.rdf_graph.query(q)

        logging.info("Number of queried entities (min/max): %d " % len(qres))

        res = []
        for row in qres:
            print row
            for r in row:
                if r.datatype == XSD.integer:
                    res.append(int(r))
                else:
                    res.append(float(r))
        xmin = res[0]        
        xmax = res[1]
        ymin = res[2]
        ymax = res[3]
        return xmin, xmax, ymin, ymax
