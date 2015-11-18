import time
import math
import re
import logging
import json

from SPARQLWrapper import SPARQLWrapper, JSON
from urlparse import urlparse

from utils import center_of_mass
from utils.aa_conversion import from_name_to_3_letters, atom, aa_name_3
from utils.color_by_residue import aa_1_3, aa_3_1

#logging.basicConfig(filename='pymol_session.log',filemode='w',level=logging.DEBUG)

class RDF_Handler:
    def __init__(self, server, uri, rules, prefix, graph, scale='Model'):
        #self.main_handler = main_handler
        # self.rdf_graph = Graph()
        self.scale = scale
        self.scales = ["Model", "Chain", "Residue", "Atom"]
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

    def create_JSON(self, x_query_type, y_query_type, scale, filter= None):
        # Query points to draw plot
        """
        Query points to draw plots
        :param x_query_type: nature of x values
        :param y_query_type: nature of y values
        """
        scale = scale or self.scale

        if not filter:
            logging.info("NO FILTER")
            points = self.query_rdf(x_query_type, y_query_type, scale.capitalize())
        else:
            logging.info("FILTER: %s " % filter)
            points = self.query_rdf_filtered(x_query_type, y_query_type, filter, scale.capitalize())

        ### Create dictionary for json
        all_models = set()
        json_dic = {'values': []}
        for row in points:
            if int(row[2]) not in all_models:
                json_dic['values'].append({'id': int(row[2]), "x": float(row[0]), "y": float(row[1])})
                # res_dic[x_query_type] = float(row[0])
                # res_dic[y_query_type] = float(row[1])
                all_models.add(int(row[2]))
        json_dic['type'] = []
        json_dic['type'].append({'x_type': x_query_type, 'y_type': y_query_type})
        json_dic['nb'] = []
        json_dic['nb'].append({'nb_models': len(all_models)})

        xmin, xmax, ymin, ymax = self.get_mini_maxi_values(x_query_type, y_query_type, scale.capitalize())
        json_dic['dim'] = []
        json_dic['dim'].append({'xmin': float(xmin), 'xmax': float(xmax), 'ymin': float(ymin), 'ymax': float(ymax)})

        json_string = json.dumps(json_dic)
        logging.debug("json dictionary: \n%s" % json_string)

        import os.path
        file_name = "%s_%s_%s.json" % (scale.lower(), x_query_type, y_query_type)
        file_path = "/Users/trellet/Dev/Visual_Analytics/PyMol_Interactive_Plotting/flask/static/json/%s" % file_name
        # if not os.path.exists(file_path):
        output = open(file_path, 'w')
        output.write(json_string)
        output.close()

        return file_name

        # logging.info("Send new plots information on server %s " % self.osc_sender.url)
        # liblo.send(('chm6048.limsi.fr',8000), '/new_plots', x_query_type, y_query_type)



    def query_sub_rdf(self, canvas, xlow, xhigh, ylow, yhigh, scale=None):
        """ Query the RDF graph for specific range of values made by user selection """
        scale = scale or self.scale
        logging.info(scale)
        query = 'SELECT ?id FROM <%s> WHERE { ?model my:%s ?y . FILTER (?y > %s && ?y < %s) . ?model my:%s ?x . FILTER ' \
                '(?x > %s && ?x < %s) . ?model my:%s_id ?id .}' % (self.uri, str(canvas.y_query_type), str(ylow),
                                                                   str(yhigh), str(canvas.x_query_type), str(xlow),
                                                                   str(xhigh), str(scale.lower()))
        logging.info("QUERY: \n%s" % query)
        self.sparql_wrapper.setQuery(self.rules+self.prefix+query)
        qres = self.sparql_wrapper.query().convert()

        logging.info("Number of queried entities: %d " % len(qres["results"]["bindings"]))

        models = set()
        for result in qres["results"]["bindings"]:
            models.add(int(result["id"]["value"]))

        return models

    def query_rdf_filtered(self, x_query_type, y_query_type, filter_ids, scale=None):
        """ Query the RDF graph to build complete plot with a filter"""
        scale = scale or self.scale
        logging.info(scale)

        # ids = tuple([int(i) for i in filter_ids])
        # Remove the final comma when only one id is in the tuple
        # if len(ids) == 1:
        #     ids_str = str(ids).replace(',','')
        # else:
        #     ids_str = str(ids)
        # print ids_str

        filter_lvls = [lvl for lvl in filter_ids if len(filter_ids[lvl]) > 0]
        logging.info(filter_lvls)

        indivs = []
        last_filter_lvl = ''
        for lvl in self.scales:
            if lvl.lower() in filter_lvls:
                logging.info("Apply filter: %s" % lvl.lower())
                ids = tuple([int(i) for i in filter_ids[lvl.lower()]])
                if len(ids) == 1:
                    ids_str = str(ids).replace(',','')
                else:
                    ids_str = str(ids)
                logging.info("ids_str: %s" % ids_str)

                if not indivs:
                    query = 'SELECT ?ind FROM <%s> WHERE { ?ind a my:%s . ?ind my:%s_id ?id . filter(?id in %s)}' % (self.uri,
                                                                                         lvl.capitalize(),
                                                                                         lvl.lower(),
                                                                                         ids_str)
                else:
                    if len(indivs) == 1:
                        indivs_str = str(tuple(indivs)).replace(',','')
                    else:
                        indivs_str = str(tuple(indivs))
                    logging.info("indivs_str: %s" % indivs_str)
                    query = 'SELECT ?ind FROM <%s> WHERE { ?ind a my:%s . ?ind my:%s_id ?id . filter(?id in %s) . ' \
                            '?ind my:belongs_to ?parent . filter (?parent in %s) }' % (self.uri, lvl.capitalize(),
                                                                                       lvl.lower(), ids_str, indivs_str)

                logging.info("QUERY: \n%s" % query)
                self.sparql_wrapper.setQuery(self.rules+self.prefix+query)
                qres = self.sparql_wrapper.query().convert()

                logging.info("Number of queried entities: %d" % (len(qres["results"]["bindings"])))

                for i in range(0,len(qres["results"]["bindings"])):
                    indivs.append(str(qres["results"]["bindings"][i]["ind"]["value"].replace(self.graph_name,"my:")))
                last_filter_lvl = lvl.lower()
                logging.info("Indivs: %s" % indivs)

        indivs_str = ''
        if len(indivs) == 1:
            indivs_str = str(tuple(indivs)).replace(',','').replace('\'','')
        else:
            indivs_str = str(tuple(indivs)).replace('\'','')
        logging.info("indivs_str after filtering: %s" % indivs_str)

        query = 'SELECT ?x ?y FROM <%s> WHERE { ?ind my:%s ?x . ?ind my:%s ?y . ?ind a my:%s . ?ind my:belongs_to ?parent ' \
                '. ?parent a my:%s . filter(?parent in %s)}'\
                % (self.uri, x_query_type, y_query_type, scale.capitalize(), last_filter_lvl.capitalize(), indivs_str)

        query2 = 'SELECT ?id FROM <%s> WHERE { ?ind a my:%s . ?ind my:uniq_id ?id . ?ind my:belongs_to ?parent ' \
                '. ?parent a my:%s . filter(?parent in %s)}' % (self.uri, scale,last_filter_lvl.capitalize(), indivs_str)

        logging.info("QUERY: \n%s" % query)
        self.sparql_wrapper.setQuery(self.rules+self.prefix+query)
        qres = self.sparql_wrapper.query().convert()
        logging.info("QUERY 2: \n%s" % query2)
        self.sparql_wrapper.setQuery(self.rules+self.prefix+query2)
        qres2 = self.sparql_wrapper.query().convert()

        logging.info("Number of queried entities: %d %d" % (len(qres["results"]["bindings"]), len(qres2["results"]["bindings"])))

        points = []
        for i in range(0,len(qres["results"]["bindings"])):
            points.append([ qres["results"]["bindings"][i]["x"]["value"], qres["results"]["bindings"][i]["y"]["value"] ])
            points[i].append(qres2["results"]["bindings"][i]["id"]["value"])

        return points


    def query_rdf(self, x_query_type, y_query_type, scale=None):
        """ Query the RDF graph to build complete plot """
        scale = scale or self.scale
        logging.info(scale)
        # query = u"""SELECT ?x ?y FROM <%s> WHERE { ?point rdf:type my:Point . ?point my:Y_type "%s" . ?point my:Y_value ?y . ?point my:X_type "%s" . ?point my:X_value ?x . ?point my:represent ?mod . ?mod my:%s_id ?id .}""" % (self.uri, y_query_type, x_query_type, scale.lower())
        # query2 = u"""SELECT ?id FROM <%s> WHERE { ?point rdf:type my:Point . ?point my:Y_type "%s" . ?point my:Y_value ?y . ?point my:X_type "%s" . ?point my:X_value ?x . ?point my:represent ?mod . ?mod my:%s_id ?id .}""" % (self.uri, y_query_type, x_query_type, scale.lower())

        query = 'SELECT ?x ?y FROM <%s> WHERE { ?model my:%s ?x . ?model my:%s ?y . ?model a my:%s . ?model my:%s_id ?id}'\
                % (self.uri, x_query_type, y_query_type, scale.capitalize(), scale.lower())
        # query2 = 'SELECT ?id FROM <%s> WHERE { ?model a my:%s . ?model my:%s_id ?id}' % (self.uri, scale, scale.lower())
        query2 = 'SELECT ?id FROM <%s> WHERE { ?model a my:%s . ?model my:uniq_id ?id}' % (self.uri, scale.capitalize())
        
        logging.info("QUERY: \n%s" % query)
        self.sparql_wrapper.setQuery(self.rules+self.prefix+query)
        qres = self.sparql_wrapper.query().convert()

        self.sparql_wrapper.setQuery(self.rules+self.prefix+query2)
        qres2 = self.sparql_wrapper.query().convert()

        logging.info("Number of queried entities: %d %d" % (len(qres["results"]["bindings"]), len(qres2["results"]["bindings"])))

        points = []
        for i in range(0,len(qres["results"]["bindings"])):
            points.append([ qres["results"]["bindings"][i]["x"]["value"], qres["results"]["bindings"][i]["y"]["value"] ])
            points[i].append(qres2["results"]["bindings"][i]["id"]["value"])

        return points

    def get_ids(self, x_query_type, y_query_type, scale=None):
        """
        :param x_query_type: type of values to plot on the abscissa
        :param y_query_type: type of values to plot on the ordered
        :param scale: hierarchical level of query
        :return: list of ids
        """
        scale = scale or self.scale
        query = 'SELECT ?id FROM <%s> WHERE { ?model a my:%s . ?model my:%s_id ?id}' % (self.uri, scale.capitalize(), scale.lower())

        logging.info("QUERY: \n%s" % query)
        self.sparql_wrapper.setQuery(self.rules+self.prefix+query)
        qres = self.sparql_wrapper.query().convert()

        ids = []

        for i in qres["results"]["bindings"]:
            ids.append(i["id"]["value"])

        return ids

    def get_info_uniq(self, uniq_id, scale=None):
        """ Get all literal information for a specific individual """
        scale = scale or self.scale
        query = 'SELECT DISTINCT ?param ?val FROM <%s> WHERE { ?model my:%s_id ?id . FILTER ( ?id = %s ) . ' \
                '?model ?param ?o . filter (isLiteral(?o)) . ?model ?param ?val}'\
                % (self.uri, scale.lower(), uniq_id)
        logging.info("QUERY: \n%s" % query)
        self.sparql_wrapper.setQuery(self.rules+self.prefix+query)
        qres = self.sparql_wrapper.query().convert()

        logging.info("Number of queried entities: %d " % len(qres["results"]["bindings"]))
        res = {}
        logging.info(qres)
        import re
        for row in qres["results"]["bindings"]:
            parsed=re.sub(r"http://www.semanticweb.org/trellet/ontologies/2015/0/VisualAnalytics#", r"", row["param"]["value"])
            try:
                res[parsed] = int(row["val"]["value"])
            except ValueError:
                res[parsed] = float(row["val"]["value"])

        return res

    def get_analyses(self, scale=None):
        """ Get which analyses already exist for specific scale """
        scale = scale or self.scales

        if type(scale) is list:
            results = {}
            for s in scale:
                query = 'SELECT DISTINCT ?param FROM <%s> WHERE { ?model ?param ?o . ?model a my:%s . filter (isLiteral(?o))}'\
                % (self.uri, s)
                logging.info("QUERY: \n%s" % query)
                self.sparql_wrapper.setQuery(self.rules+self.prefix+query)
                qres = self.sparql_wrapper.query().convert()

                logging.info("Number of queried entities: %d " % len(qres["results"]["bindings"]))
                results[s] = []
                import re
                for row in qres["results"]["bindings"]:
                    parsed=re.sub(r"http://www.semanticweb.org/trellet/ontologies/2015/0/VisualAnalytics#", r"", row["param"]["value"])
                    results[s].append(parsed)
            return results
        else:
            #query = u"""SELECT DISTINCT ?x_type ?y_type FROM <%s> WHERE { ?point my:X_type ?x_type . ?point my:Y_type ?y_type . ?point my:represent ?ind . ?ind rdf:type ?type . ?type rdfs:subClassOf* my:%s .}""" % (self.uri, scale)
            query = 'SELECT DISTINCT ?param FROM <%s> WHERE { ?model ?param ?o . ?model a my:%s . filter (isLiteral(?o))}'\
                    % (self.uri, scale)
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

    def add_distance_points(self, item_selected, model_selected, scale=None):
        scale = scale or self.scale
        item_list, indiv_list = self.get_id_indiv_from_RDF(model_selected)

        if scale == "Residue":
            ref_x, ref_y, ref_z = center_of_mass.get_com("resid %s and model %04d" % (str(item_selected), model_selected))
        elif scale == "Atom":
            ref_x, ref_y, ref_z = center_of_mass.get_com("id %s and model %04d" % (str(item_selected), model_selected))
        logging.info("Coordinates of reference item: %f %f %f" % (ref_x, ref_y, ref_z))

        #my = Namespace("http://www.semanticweb.org/trellet/ontologies/2015/0/VisualAnalytics#")
        last_point_id = self.get_last_id("Point")
        nb_pt = 1
        start_time = time.time()
        rdf_insert_header = "%s\ninsert data { graph <%s> { " % (self.prefix, self.uri)
        for item in item_list:
            if item != item_selected:
                if scale == "Residue":
                    x,y,z = center_of_mass.get_com("resid %s and model %04d" % (str(item), model_selected))
                elif scale == "Atom":
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
                
                if scale == "Residue":
                    insertion += point+" "+self.prefix_name+':X_type "resid" . '
                    res = str(indiv_list[nb_pt])
                    p = re.compile("RES_[0-9]+")
                    r=p.search(res)
                    if nb_pt == 1:
                        logging.info(r.group(0))
                    insertion += point+" "+self.prefix_name+":represent "+self.prefix_name+":"+r.group(0)+" . "
                    # self.rdf_graph.add( (point, my.X_type, Literal('resid')))
                    # res = str(indiv_list[nb_pt])
                    # self.rdf_graph.add( (point, my.represent, res))
                elif scale == "Atom":
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
        query = 'SELECT ?res ?resid FROM <'+self.uri+'> WHERE{ ?res my:residue_id ?resid . ?res my:belongs_to+ my:MODEL_'\
                +str(model)+' .} ORDER BY ?resid'
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

    def get_mini_maxi_values(self, xtype, ytype, scale=None):
        """ Get minimum and maximum for x and y values from POINT individuals """
        scale = scale or self.scale
        # query = 'SELECT (MIN(?x) AS ?xmin) (MAX(?x) AS ?xmax) (MIN(?y) AS ?ymin) (MAX(?y) AS ?ymax) FROM <'+self.uri+'> WHERE { ?model my:%s ?x . ?model my:%s ?y . ?model my:X_type "'+xtype+'" . ?point my:Y_type "'+ytype+'" . ?point my:represent ?ind . ?ind rdf:type ?type . ?type rdfs:subClassOf* my:'+scale+' .}'
        query = 'SELECT (MIN(?x) AS ?xmin) (MAX(?x) AS ?xmax) (MIN(?y) AS ?ymin) (MAX(?y) AS ?ymax) FROM <%s> WHERE ' \
                '{ ?model my:%s ?x . ?model my:%s ?y . ?model a my:%s .}' % (self.uri, xtype, ytype, scale)
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

    def is_action(self, key):
        logging.debug('Key to identify: %s' % key)
        query = 'ASK {my:%s rdfs:subClassOf my:Action}' % key
        logging.debug("QUERY: \n%s" % query)

        self.sparql_wrapper.setQuery(self.rules+self.prefix+query)
        qres = self.sparql_wrapper.query().convert()

        logging.debug(qres['boolean'])
        return bool(qres['boolean'])

    def is_component(self, key):
        logging.debug('Key to identify: %s' % key)
        if from_name_to_3_letters(key):
            query = 'ASK {my:%s rdfs:subClassOf my:Biological_component}' % from_name_to_3_letters(key)
        elif aa_3_1.has_key(key.upper()):
            query = 'ASK {my:%s rdfs:subClassOf my:Biological_component}' % key.lower()
        elif key.upper() in atom:
            query = 'ASK {my:%s rdfs:subClassOf my:Biological_component}' % key.lower()
        else:
            query = 'ASK {my:%s rdfs:subClassOf my:Biological_component}' % key
        logging.debug("QUERY: \n%s" % query)

        self.sparql_wrapper.setQuery(self.rules+self.prefix+query)
        qres = self.sparql_wrapper.query().convert()

        logging.debug(qres['boolean'])
        return bool(qres['boolean'])

    def is_representation(self, key):
        logging.debug('Key to identify: %s' % key)
        query = 'ASK {my:%s rdfs:subClassOf my:Representation}' % key
        logging.debug("QUERY: \n%s" % query)

        self.sparql_wrapper.setQuery(self.rules+self.prefix+query)
        qres = self.sparql_wrapper.query().convert()

        logging.debug(qres['boolean'])
        return bool(qres['boolean'])

    def is_color(self, key):
        logging.debug('Key to identify: %s' % key)
        query = 'ASK {my:%s rdfs:subClassOf my:Colors}' % key
        logging.debug("QUERY: \n%s" % query)

        self.sparql_wrapper.setQuery(self.rules+self.prefix+query)
        qres = self.sparql_wrapper.query().convert()

        logging.debug(qres['boolean'])
        return bool(qres['boolean'])

    def is_property(self, key):
        logging.debug('Key to identify: %s' % key)
        query = 'ASK {my:%s rdfs:subClassOf my:Property}' % key
        logging.debug("QUERY: \n%s" % query)

        self.sparql_wrapper.setQuery(self.rules+self.prefix+query)
        qres = self.sparql_wrapper.query().convert()

        logging.debug(qres['boolean'])
        return bool(qres['boolean'])

    def is_id(self, key, component):
        if isinstance(key, int):
            logging.debug('Key to identify: %d \nfor component: %s' % (key, component))
            if component.capitalize() in aa_name_3:
                logging.debug("SPECIFIC AMINO-ACID")
                query = 'ASK {?s a my:%s . ?s my:residue_id ?id . FILTER ( ?id = %d ) }' % (from_name_to_3_letters(component.capitalize()).lower(), key)
            else:
                query = 'ASK {?s my:%s_id ?id . FILTER ( ?id = %d ) }' % (component.lower(), key)

        else:
            logging.debug('Key to identify: %s \nfor component: %s' % (key, component))
            query = 'ASK {?s my:%s_id ?id . FILTER ( regex(?id, "%s" )) }' % (component.lower(), key)
        logging.debug("QUERY: \n%s" % query)

        self.sparql_wrapper.setQuery(self.rules+self.prefix+query)
        qres = self.sparql_wrapper.query().convert()

        logging.debug(qres['boolean'])
        return bool(qres['boolean'])

    def check_indiv_for_selection(self, component, output, id1=None, id2=None):
        if id1 and not id2:
            logging.info("SPARQL step - One id associated")
            logging.info('Key to identify: %s for component: %s at scale: %s' % (id1, component, self.scale))
            # if self.scale.lower() == component.lower():
            #     if isinstance(id, int):
            #         query = 'SELECT DISTINCT ?r ?num FROM <%s> WHERE {?s my:%s_id ?id . FILTER ( ?id = %s ) . ?r a my:%s . ' \
            #                 '?r my:%s_id ?num}' % (self.uri, component.lower(), id, self.scale.capitalize(), self.scale.lower())
            #     else:
            #         query = 'SELECT DISTINCT ?r ?num FROM <%s> WHERE {?s my:%s_id ?id . FILTER ( regex(?id, "%s") ) . ?r a my:%s . ?r my:belongs_to ' \
            #                 '?s . ?r my:%s_id ?num}' % (self.uri, component.lower(), id, self.scale.capitalize(), self.scale.lower())
            # else:
            if isinstance(id1, int):
                query = 'SELECT DISTINCT ?r ?num FROM <%s> WHERE {?s my:%s_id ?id . FILTER ( ?id = %s ) . ?r a my:%s . ?r my:belongs_to ?s . ' \
                        '?r my:%s_id ?num}' % (self.uri, component.lower(), id1, self.scale.capitalize(), self.scale.lower())
            else:
                query = 'SELECT DISTINCT ?r ?num FROM <%s> WHERE {?s my:%s_id ?id . FILTER ( regex(?id, "%s") ) . ?r a my:%s . ?r my:belongs_to ' \
                        '?s . ?r my:%s_id ?num}' % (self.uri, component.lower(), id1, self.scale.capitalize(), self.scale.lower())
        elif id1 and id2:
            logging.info("SPARQL step - 2 ids")
            logging.info('Key to identify: from %s to %s for component: %s at scale: %s' % (id1, id2, component, self.scale))
            if component.capitalize() in aa_name_3:
                query = 'SELECT DISTINCT ?r ?num FROM <%s> WHERE {?s a my:%s . ?s my:residue_id ?id . FILTER ( ?id > %s && ?id < %s ) . ?r a my:%s . ' \
                            '?r my:%s_id ?num}' % (self.uri, from_name_to_3_letters(component.capitalize()).lower(), id1, id2, self.scale.capitalize(), self.scale.lower())
            else:
                query = 'SELECT DISTINCT ?r ?num FROM <%s> WHERE {?s my:%s_id ?id . FILTER ( ?id > %s && ?id < %s ) . ?r a my:%s . ' \
                            '?r my:%s_id ?num}' % (self.uri, component.lower(), id1, id2, self.scale.capitalize(), self.scale.lower())
        else:
            logging.info("SPARQL step - No id")
            logging.info('Component: %s' % component)
            if component.capitalize() in aa_name_3:
                query = 'SELECT DISTINCT ?r ?num FROM <%s> WHERE {?r a my:%s . ?r my:%s_id ?num}' % (self.uri, from_name_to_3_letters(component.capitalize()).lower(), self.scale.lower())
            else:
                query = 'SELECT DISTINCT ?r ?num FROM <%s> WHERE {?r a my:%s . ?r my:%s_id ?num}' % (self.uri, component.capitalize(), self.scale.lower())

        logging.info('QUERY: %s' % query)

        self.sparql_wrapper.setQuery(self.rules+self.prefix+query)
        qres = self.sparql_wrapper.query().convert()

        indivs_ids = []
        indivs_uri = []

        for row in qres["results"]["bindings"]:
            indivs_ids.append(int(row["num"]["value"]))
            indivs_uri.append(row["r"]["value"])

        indivs_set = set(indivs_ids)
        indivs_ids = list(indivs_set)

        indivs_set = set(indivs_uri)
        indivs_uri = list(indivs_set)

        if output == 'ids':
            return indivs_ids
        elif output == 'uri':
            return indivs_uri

    def check_indiv_for_property(self, property):
        logging.info('Property: %s' % (property))
        query = 'SELECT DISTINCT ?num FROM <%s> WHERE {?r a my:%s . ?r a my:%s . ?r my:%s_id ?num}' % (self.uri, self.scale.capitalize(),
                                                                                  property.capitalize(), self.scale.lower())

        logging.info("QUERY: \n%s" % query)

        self.sparql_wrapper.setQuery(self.rules+self.prefix+query)
        qres = self.sparql_wrapper.query().convert()

        indivs = []
        for row in qres["results"]["bindings"]:
            indivs.append(int(row["num"]["value"]))

        return indivs

    def requirement_for_action(self, action):
        logging.info('Requirement(s) for action: %s' % action)
        query = 'SELECT DISTINCT ?req FROM <%s> WHERE {?a rdfs:subClassOf my:%s . ?a rdfs:subClassOf ?restriction . ?restriction ' \
                'owl:someValuesFrom ?req}' % (self.uri, action.capitalize())

        logging.info('QUERY: %s' % query)

        self.sparql_wrapper.setQuery(self.rules+self.prefix+query)
        qres = self.sparql_wrapper.query().convert()

        requirements = []
        for row in qres['results']['bindings']:
            o = urlparse(row["req"]["value"])
            requirements.append(o.fragment)

        return requirements

    def are_equivalent(self, v, w):
        logging.debug("Are %s and %s equivalent?" % (v,w))
        query = 'SELECT DISTINCT ?m WHERE {{?a rdfs:subClassOf my:%s . ?a owl:equivalentClass ?restriction . ' \
                '?restriction owl:unionOf ?list . ?list rdf:rest*/rdf:first ?m} union {my:%s owl:equivalentClass ?m } ' \
                'union {?m owl:equivalentClass my:%s} }' % (v, v, v)
        logging.debug('QUERY: %s' % query)

        self.sparql_wrapper.setQuery(self.rules+self.prefix+query)
        qres = self.sparql_wrapper.query().convert()

        for row in qres['results']['bindings']:
            o = urlparse(row['m']['value'])
            if o.fragment == w:
                return True

        return False

    def from_uniq_to_bio_ids(self, scale, selected):
        logging.debug("Converting uniq ids %s to biologically meaningful ids" % selected)

        selected_str = ''
        if len(selected) == 1:
            selected_str = str(tuple(selected)).replace(',','').replace('\'','')
        else:
            selected_str = str(tuple(selected)).replace('\'','')
        logging.info(selected_str)

        query = 'SELECT ?id FROM <%s> WHERE { ?ind a my:%s . ?ind my:%s_id ?id . ?ind my:uniq_id ?uniq . filter(?uniq in %s)}' \
                % (self.uri, scale.capitalize(), scale.lower(), selected_str)

        self.sparql_wrapper.setQuery(self.rules+self.prefix+query)
        qres = self.sparql_wrapper.query().convert()

        bio_ids = []
        for row in qres["results"]["bindings"]:
            bio_ids.append(int(row["id"]["value"]))

        return bio_ids

    def from_uniq_to_hierarchical_tree(self, scale, selected):

        ids = tuple([int(i) for i in selected])
        if len(ids) == 1:
            ids_str = str(ids).replace(',','')
        else:
            ids_str = str(ids)
        logging.debug(ids_str)

        hierarchical_tree = {}
        hierarchical_tree = hierarchical_tree.fromkeys(selected, {'model':[], 'chain':[], 'residue':[], 'atom':[]})
        logging.debug(hierarchical_tree)
        for sel in selected:
            logging.debug("New uniq id: %s " % sel)
            hierarchical_tree[sel] = {'model':None, 'chain':None, 'residue':None, 'atom':None}
            for lvl in self.scales:
                logging.debug("New level: %s " % lvl)
                if lvl.lower() == scale:
                    query = 'SELECT ?id FROM <%s> WHERE { ?ind a my:%s . ?ind my:uniq_id ?uniq . FILTER ( ?uniq = %s ) . ' \
                            '?ind my:%s_id ?id .}' % (self.uri, scale.capitalize(), str(sel), lvl.lower())
                    logging.debug(query)
                    self.sparql_wrapper.setQuery(self.rules+self.prefix+query)
                    qres = self.sparql_wrapper.query().convert()
                    logging.debug(qres["results"]["bindings"][0]["id"]["value"])
                    parent_id = qres["results"]["bindings"][0]["id"]["value"]
                    if parent_id.isdigit():
                        hierarchical_tree[sel][lvl.lower()] = int(parent_id)
                    else:
                        hierarchical_tree[sel][lvl.lower()] = parent_id
                    break
                else:
                    query = 'SELECT ?id FROM <%s> WHERE { ?ind a my:%s . ?ind my:uniq_id ?uniq . FILTER ( ?uniq = %s ) . ' \
                            '?ind my:belongs_to ?parent . ?parent my:%s_id ?id .}' % (self.uri, scale.capitalize(), str(sel), lvl.lower())

                    self.sparql_wrapper.setQuery(self.rules+self.prefix+query)
                    qres = self.sparql_wrapper.query().convert()
                    parent_id = qres["results"]["bindings"][0]["id"]["value"]
                    if parent_id.isdigit():
                        hierarchical_tree[sel][lvl.lower()] = int(parent_id)
                    else:
                        hierarchical_tree[sel][lvl.lower()] = parent_id
        logging.info(hierarchical_tree)
        return hierarchical_tree