import time
import math
import re
import logging

from SPARQLWrapper import SPARQLWrapper, JSON

from utils import center_of_mass

# logging.basicConfig(filename='pymol_session.log',filemode='w',level=logging.INFO)

class RDF_Handler:
    def __init__(self, server, uri, rules, prefix, graph, scale='Model'):
        #self.main_handler = main_handler
        # self.rdf_graph = Graph()
        self.scale = scale
        self.distant_server = server
        self.uri = uri
        self.rules_name = rules
        self.prefix_name = prefix
        self.graph_name = graph
        # To force Virtuoso to use inference rules (RDFS and OWL)
        self.rules = 'define input:inference "'+self.rules_name+'" '
        self.prefix = 'prefix '+self.prefix_name+':<'+self.graph_name+'> '
        self.sparql_wrapper = SPARQLWrapper(self.distant_server)
        self.sparql_wrapper.setReturnFormat(JSON)
        logging.info(self.distant_server)
        logging.info(self.rules)
        logging.info(self.prefix)
        logging.info(self.uri)

    def set_scale(self,scale):
        pass


    def query_sub_rdf(self, canvas, xlow, xhigh, ylow, yhigh):
        """ Query the RDF graph for specific range of values made by user selection """
        
        
        query = 'SELECT ?id FROM <%s> WHERE { ?model my:%s ?y . FILTER (?y > %s && ?y < %s) . ?model my:%s ?x . FILTER ' \
                '(?x > %s && ?x < %s) . ?model my:%s_id ?id .}' % (self.uri, str(canvas.y_query_type), str(ylow),
                                                                   str(yhigh), str(canvas.x_query_type), str(xlow),
                                                                   str(xhigh), str(self.scale.lower()))
        logging.info("QUERY: \n%s" % query)
        self.sparql_wrapper.setQuery(self.rules+self.prefix+query)
        qres = self.sparql_wrapper.query().convert()

        logging.info("Number of queried entities: %d " % len(qres["results"]["bindings"]))

        models = set()
        for result in qres["results"]["bindings"]:
            models.add(int(result["id"]["value"]))

        return models

    def query_rdf(self, x_query_type, y_query_type):
        """ Query the RDF graph to build complete plot """
        
        # query = u"""SELECT ?x ?y FROM <%s> WHERE { ?point rdf:type my:Point . ?point my:Y_type "%s" . ?point my:Y_value ?y . ?point my:X_type "%s" . ?point my:X_value ?x . ?point my:represent ?mod . ?mod my:%s_id ?id .}""" % (self.uri, y_query_type, x_query_type, scale.lower())
        # query2 = u"""SELECT ?id FROM <%s> WHERE { ?point rdf:type my:Point . ?point my:Y_type "%s" . ?point my:Y_value ?y . ?point my:X_type "%s" . ?point my:X_value ?x . ?point my:represent ?mod . ?mod my:%s_id ?id .}""" % (self.uri, y_query_type, x_query_type, scale.lower())

        query = """SELECT ?x ?y FROM <%s> WHERE { ?model my:%s ?x . ?model my:%s ?y . ?model a my:%s . ?model my:%s_id
        ?id}""" % (self.uri, x_query_type, y_query_type, self.scale, self.scale.lower())
        query2 = """SELECT ?id FROM <%s> WHERE { ?model a my:%s . ?model my:%s_id ?id}""" % (self.uri, self.scale, self.scale.lower())
        
        logging.info("QUERY: \n%s" % query)
        self.sparql_wrapper.setQuery(self.rules+self.prefix+query)
        qres = self.sparql_wrapper.query().convert()

        self.sparql_wrapper.setQuery(self.rules+self.prefix+query2)
        qres2 = self.sparql_wrapper.query().convert()

        logging.info("Number of queried entities: %d " % len(qres["results"]["bindings"]))

        points = []

        for i in range(0,len(qres["results"]["bindings"])):
            points.append([ qres["results"]["bindings"][i]["x"]["value"], qres["results"]["bindings"][i]["y"]["value"] ])
            points[i].append(qres2["results"]["bindings"][i]["id"]["value"])
        # for res in qres["results"]["bindings"]:
        #     points.append( [res["x"]["value"], res["y"]["value"], res["id"]["value"]])
        # in qres["results"]["bindings"]:
        #     points.append([ res["x"]["value"], res["y"]["value"] ])

        return points

    def get_analyses(self):
        """ Get which analyses already exist for specific scale """

        #query = u"""SELECT DISTINCT ?x_type ?y_type FROM <%s> WHERE { ?point my:X_type ?x_type . ?point my:Y_type ?y_type . ?point my:represent ?ind . ?ind rdf:type ?type . ?type rdfs:subClassOf* my:%s .}""" % (self.uri, scale)
        query = u"""SELECT DISTINCT ?param FROM <%s> WHERE { ?model ?param ?o . ?model a my:%s . filter (isLiteral(?o))}""" % (self.uri, self.scale)
        logging.info("QUERY: \n%s" % query)
        self.sparql_wrapper.setQuery(self.rules+self.prefix+query)
        qres = self.sparql_wrapper.query().convert()

        logging.info("Number of queried entities: %d " % len(qres["results"]["bindings"]))
        res = []
        import re
        for row in qres["results"]["bindings"]:
            parsed=re.sub(r"http://www.semanticweb.org/trellet/ontologies/2015/0/VisualAnalytics#", r"", row["param"]["value"])
            res.append(parsed)

        return res

    def add_distance_points(self, item_selected, model_selected):
        item_list, indiv_list = self.get_id_indiv_from_RDF(model_selected)

        if self.scale == "Residue":
            ref_x, ref_y, ref_z = center_of_mass.get_com("resid %s and model %04d" % (str(item_selected), model_selected))
        elif self.scale == "Atom":
            ref_x, ref_y, ref_z = center_of_mass.get_com("id %s and model %04d" % (str(item_selected), model_selected))
        logging.info("Coordinates of reference item: %f %f %f" % (ref_x, ref_y, ref_z))

        #my = Namespace("http://www.semanticweb.org/trellet/ontologies/2015/0/VisualAnalytics#")
        last_point_id = self.get_last_id("Point")
        nb_pt = 1
        start_time = time.time()
        rdf_insert_header = "%s\ninsert data { graph <%s> { " % (self.prefix, self.uri)
        for item in item_list:
            if item != item_selected:
                if self.scale == "Residue":
                    x,y,z = center_of_mass.get_com("resid %s and model %04d" % (str(item), model_selected))
                elif self.scale == "Atom":
                    x,y,z = center_of_mass.get_com("id %s and model %04d" % (str(item), model_selected))
                logging.info("Coordinates x y z : %f %f %f " % (x,y,z))
                dist = math.sqrt(math.pow((ref_x-x),2)+math.pow((ref_y-y),2)+math.pow((ref_z-z),2))
                logging.info("Distance: %f" % dist)
                
                # point = URIRef(my+"POINT_"+str(last_point_id+nb_pt))
                # self.rdf_graph.add( (point, RDF.type, my.point) )
                # self.rdf_graph.add( (point, my.X_value, Literal(item)) )
                # self.rdf_graph.add( (point, my.Y_value, Literal(dist)))

                point = self.prefix_name+':POINT_'+str(last_point_id+nb_pt)
                insertion = point+" rdf:type "+self.prefix_name+":Point . "
                insertion += point+" "+self.prefix_name+":X_value "+str(item)+" . "
                insertion += point+" "+self.prefix_name+":Y_value "+str(dist)+" . "
                
                if self.scale == "Residue":
                    insertion += point+" "+self.prefix_name+':X_type "resid" . '
                    res = str(indiv_list[nb_pt])
                    p = re.compile("RES_[0-9]+")
                    r=p.search(res)
                    if nb_pt == 1:
                        print r.group(0)
                    insertion += point+" "+self.prefix_name+":represent "+self.prefix_name+":"+r.group(0)+" . "
                    # self.rdf_graph.add( (point, my.X_type, Literal('resid')))
                    # res = str(indiv_list[nb_pt])
                    # self.rdf_graph.add( (point, my.represent, res))
                elif self.scale == "Atom":
                    insertion += point+" "+self.prefix_name+":X_type atomid . "
                    at = str(indiv_list[nb_pt])
                    insertion += point+" "+self.prefix_name+":represent "+at+" . "
                insertion += point+" "+self.prefix_name+':Y_type "distance" . } }'
                # self.rdf_graph.add( (point, my.Y_type, Literal('distance')))

                query = rdf_insert_header+insertion
                self.sparql_wrapper.setQuery(self.rules+query)
                qres = self.sparql_wrapper.query().convert()
                if nb_pt == 2:
                    logging.info(qres)

                nb_pt += 1

        logging.info("---- %s seconds ----" % str(time.time()-start_time))
        logging.info("Number of queried entities: %d " % nb_pt)


    def get_id_indiv_from_RDF(self, model):
        query = 'SELECT ?res ?resid FROM <'+self.uri+'> WHERE{ ?res my:residue_id ?resid . ?res my:belongs_to+ my:MODEL_'+str(model)+' .} ORDER BY ?resid'
        logging.info("QUERY: \n%s" % query)

        self.sparql_wrapper.setQuery(self.rules+self.prefix+query)
        qres = self.sparql_wrapper.query().convert()

        logging.info("Number of queried entities: %d " % len(qres["results"]["bindings"]))

        id_list = []
        indiv_list = []

        for res in qres["results"]["bindings"]:
            id_list.append(int(res["resid"]["value"]))
            indiv_list.append(res["res"]["value"])
            logging.info("indiv: %s / id: %d" % (indiv_list[-1], id_list[-1]))

        return id_list, indiv_list

    def get_last_id(self, type):
        query = """SELECT ?id FROM <%s> WHERE {?id rdf:type my:%s .}""" % (self.uri, type)
        logging.info("QUERY: \n%s" % query)

        self.sparql_wrapper.setQuery(self.rules+self.prefix+query)
        qres = self.sparql_wrapper.query().convert()

        list_id = []
        import re
        p = re.compile("POINT_(.*)")
        for res in qres["results"]["bindings"]:
            tmp = p.search(res["id"]["value"])
            list_id.append(int(tmp.groups()[0]))

        list_id.sort()
        return list_id[-1]

    def get_mini_maxi_values(self, xtype, ytype):
        """ Get minimum and maximum for x and y values from POINT individuals """

        # query = 'SELECT (MIN(?x) AS ?xmin) (MAX(?x) AS ?xmax) (MIN(?y) AS ?ymin) (MAX(?y) AS ?ymax) FROM <'+self.uri+'> WHERE { ?model my:%s ?x . ?model my:%s ?y . ?model my:X_type "'+xtype+'" . ?point my:Y_type "'+ytype+'" . ?point my:represent ?ind . ?ind rdf:type ?type . ?type rdfs:subClassOf* my:'+scale+' .}'
        query = """SELECT (MIN(?x) AS ?xmin) (MAX(?x) AS ?xmax) (MIN(?y) AS ?ymin) (MAX(?y) AS ?ymax) FROM <%s> WHERE
        { ?model my:%s ?x . ?model my:%s ?y . ?model a my:%s .}""" % (self.uri, xtype, ytype, self.scale)
        logging.info("QUERY: \n%s" % query)

        self.sparql_wrapper.setQuery(self.rules+self.prefix+query)
        qres = self.sparql_wrapper.query().convert()

        logging.info("Number of queried entities (min/max): %d " % len(qres["results"]["bindings"]))

        tmp = []
        res = []
        for row in qres["results"]["bindings"]:
            tmp = [row["xmin"]["value"], row["xmax"]["value"], row["ymin"]["value"], row["ymax"]["value"]]
            for r in tmp:
                try:
                    res.append(int(r))
                except ValueError:
                    res.append(float(r))

        xmin = res[0]    
        xmax = res[1]
        ymin = res[2]
        ymax = res[3]

        return xmin, xmax, ymin, ymax
