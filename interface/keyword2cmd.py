from RDFHandler.RDF_handling_distant import RDF_Handler
from utils.aa_conversion import aa_name_3

import logging
import sys
import time

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s')


__author__ = 'trellet'

component_hierarchical_level = {"Model":4, "Chain":3, "Residue":2, "Atom": 1}

class Keyword2Cmd:

    def __init__(self, keywords, sub_selection=None):
        self.keywords = self.convert_to_OWL_format(keywords)
        self.rdf_handler=RDF_Handler("http://localhost:8890/sparql", "http://peptide_traj_21072015.com",
                                     "http://peptide_traj_21072015.com/rules", "my",
                                     "http://www.semanticweb.org/trellet/ontologies/2015/0/VisualAnalytics#")
        self.sub_selection = sub_selection
        self.rdf_handler.scale = 'Residue'

    def translate(self):
        action = []
        representation = []
        color = []
        selection = []
        types = ['action', 'representation', 'color', 'component', 'property', 'id']
        command = ''
        previous = None

        # We remove equivalent keywords
        for k in self.keywords:
            for l in self.keywords:
                if k != l and isinstance(k, str) and isinstance(l, str):
                    if self.rdf_handler.are_equivalent(k,l):
                        logging.info("The keyword %s has been removed because equivalent to %s" % (l,k))
                        self.keywords.remove(l)

        # We identify each keyword type and family
        previous_component_index = 0
        for key in self.keywords:
            # We check for id associated to the component
            if previous == 'component' and isinstance(key, list):
                logging.info("CASE 1: Component + Range of ids")
                if not isinstance(key[0], int) or not isinstance(key[1], int):
                    logging.error('You cannot have non integer values for a range of ids')
                selection.append((key[0], 'from'))
                selection.append((key[1], 'to'))
                previous = types[3]
                previous_component_index = len(selection)-1
            # elif previous == 'id' and self.rdf_handler.is_id(key, selection[previous_component_index][0]):
            #     logging.info("CASE 2: Component + Id + Another Id")
            #     selection.append((key, 'id'))
            #     previous = types[5]
            elif previous == 'component' and self.rdf_handler.is_id(key, selection[previous_component_index][0]):
                logging.info("CASE 2: Component <%s> + id <%s>" % (selection[previous_component_index], key))
                selection.append((key, 'id'))
                # previous = types[5]
            elif self.rdf_handler.is_action(key):
                action.append(key)
                previous = types[0]
            elif isinstance(key, str) and self.rdf_handler.is_component(key):
                selection.append((key, 'component'))
                previous = types[3]
                previous_component_index = len(selection)-1
            elif self.rdf_handler.is_representation(key):
                representation.append(key)
                previous = types[1]
            elif self.rdf_handler.is_color(key):
                color.append(key)
                previous = types[2]
            elif self.rdf_handler.is_property(key):
                selection.append((key, 'property'))
                previous = types[4]
            else:
                logging.error("We identified an id (%s) without any component associated" % key)

        # # Remove equivalent properties (Charge and Positive for ex.)
        # if len([item for item in selection if 'property' in item]) > 0:
        #     values = [item[0] for item in selection if item[1] == 'property']
        #     for v in values:
        #         for w in values:
        #             if v != w:
        #                 if self.rdf_handler.are_equivalent(v,w):
        #                     selection.remove((w,'property'))
        #     print selection
        #
        # # Remove equivalent representation (Secondary_structure and Cartoon for ex.)
        # if len(representation) > 1:
        #     for v in representation:
        #         for w in representation:
        #             if v != w:
        #                 if self.rdf_handler.are_equivalent(v, w):
        #                     representation.remove(v)
        #                     break
        #     print representation

        ids=[]
        # We first sort the selection for better handling of multilvl components
        # COMPONENT
        logging.info("Selection: " + str(selection))
        number_of_components = len([c for c in selection if c[1]=="component"])
        components = [c for c in selection if c[1]=="component" or c[1]=="id"]
        logging.info(components)
        if number_of_components > 0:
            ids, selection_filter = self.from_component_to_indivs(components, number_of_components)
        
        ids_components = set(ids)
        ids = []
        print ids_components

        # PROPERTY
        properties = [p for p in selection if p[1]=="property"]
        if len(properties) > 0:
            ids = self.from_property_to_indivs(properties)

        ids_properties = set(ids)
        print ids_properties

        if ids_properties and ids_components:
            ids = list(ids_properties.intersection(ids_components))
        elif ids_components:
            ids = list(ids_components)
        else:
            ids = list(ids_properties)
        print ids
        
        # ACTION
        if len(action) > 0:
            logging.info(action)
            for a in action:
                require = self.rdf_handler.requirement_for_action(a)
                command += a.lower()+" "
                logging.info(require)
                for r in require:
                    if r == 'Visual_representation':
                        if not representation:
                            logging.error("When you want to use %s action, you need to specify a Visual_representation" % a)
                        else:
                            command += representation[0].lower()
                        continue
                    elif r == 'Colors':
                        if not color:
                            logging.error("When you want to use %s action, you need to specify a Color" % a)
                        else:
                            command += color[0].lower()
                        continue
                    elif r == 'Object':
                        if not ids:
                            logging.error("When you want to use %s action, you need to specify a Selection" % a)
                        else:
                            command += self.rdf_handler.scale.lower()+" "
                            for i in ids:
                                command +='%s+' % str(i)
                            command = command[:-1]
                            command += " "
                        continue
        if ids:
            command += ", %s " % self.rdf_handler.scale.lower()
            for i in ids:
                command +='%s+' % str(i)
            command = command[:-1]
            command += " "

        if selection_filter:
            for s in selection_filter:
                if s[1] == "component":
                    command+=' and '
                    command+=s[0].lower()
                elif s[1] == "id":
                    command += ' '+s[0]

        logging.info(command)


    def order_selection(self, selection):
        """
        Increasingly order the component selection to get the lowest lvl component first
        :param selection: List of biological component identified in the keywords
        :return: sorted list: Ordered list of compononents
        """

        if selection == []: 
            return []
        else:
            pivot = selection[0]
            lesser = self.order_selection([x for x in selection[1:] if x < pivot])
            greater = self.order_selection([x for x in selection[1:] if x >= pivot])
            return lesser + [pivot] + greater

    def from_property_to_indivs(self, properties):
        """
        Get all the individuals ids corresponding to the properties identified in the keywords
        :param property: List of property associated
        :return: individuals: List of ids stored in RDF
        """
        indivs_from_property = []

        for i in range(0, len(properties)):
            indivs_from_property += self.rdf_handler.check_indiv_for_property(properties[i][0])
            #print indivs_from_property
            indivs_set = set(indivs_from_property)
            #print indivs_set
            indivs_from_property = list(indivs_set)

        logging.info("INDIVS from property: %s" % str(indivs_from_property))

        return indivs_from_property

    def from_component_to_indivs(self, components, number_of_components):
        """
        Get all the individuals ids corresponding to the properties identified in the keywords
        :param components: List of components and associated ids
        :return: individuals: List of ids stored in RDF
        """
        selection_filter = []
        indiv_ids_from_component = []
        for i in range(0, len(components)):
            if components[i][1] == 'component' :
                logging.info("**********" )
                logging.info("Component: %s" % str(components[i]))
                logging.info("**********") 
                if i+1 < len(components) and components[i+1][1] == 'id':
                    for j in range(i+1, len(components)):
                        if components[j][1] == 'id':
                            logging.info("There is an id")
                            # In the case where the desired output scale is equal to the component we identified
                            # We don't need to search for ids if it's already given by the keywords
                            if self.rdf_handler.scale.lower() == components[i][0].lower():
                                logging.info("Scale and component levels identical, take ids directly")
                                indiv_ids_from_component.append(components[j][0])
                            else:
                                logging.info("Scale and component levels different, check levels")
                                if components[i][0] in component_hierarchical_level:
                                    # When a higher hierarchical lvl component is found, it can be interpreted in 2 ways:
                                    # 1. If alone, all of his children of the general hierarchical lvl needs to be selected
                                    # 2. If used with another lower hierarchical lvl, we use it as filter
                                    if component_hierarchical_level[components[i][0]] > component_hierarchical_level[self.rdf_handler.scale.capitalize()]:
                                        logging.info(components[i][0]+" > "+self.rdf_handler.scale)
                                        if number_of_components > 1:
                                            selection_filter.append(components[i])
                                            # selection_filter += [component for component in components[i:] if component[1]=="id"] # Better solution?
                                            for component in components[i+1:]:
                                                print component
                                                if component[1] == "component":
                                                    break
                                                elif component[1] == "id":
                                                    selection_filter.append(component)
                                            logging.info("Filter(s) for now: %s" % str(selection_filter))
                                            break
                                        else:
                                            if components[i][0] in aa_name_3:
                                                indiv_ids_from_component += self.rdf_handler.check_indiv_for_selection(aa_name_3[components[i][0]].lower(), 'ids', components[j][0])
                                            else:
                                                indiv_ids_from_component += self.rdf_handler.check_indiv_for_selection(components[i][0], 'ids', components[j][0])
                                else:
                                    break

                                # indiv_ids_from_component += self.rdf_handler.check_indiv_for_selection(aa_name_3['selection[i][0]'], 'ids', selection[j][0])
                        else:
                            break
                elif i+1 < len(components) and components[i+1][1] == 'from':
                    if self.rdf_handler.scale.lower() == components[i][0].lower():
                        for j in range(components[i+1][0], components[i+2][0]+1):
                            indiv_ids_from_component.append(j)
                    else:
                        indiv_ids_from_component += self.rdf_handler.check_indiv_for_selection(components[i][0], 'ids',
                                                                                              components[i+1][0],
                                                                                              components[i+2][0])
                # Component is not associated to a specific id
                else:
                    logging.info("No id for %s " % str(components[i][0]))
                    if components[i][0] in aa_name_3:
                        res = aa_name_3[components[i][0]].lower()
                        indiv_ids_from_component += self.rdf_handler.check_indiv_for_selection(res, 'ids')
                    else:
                        indiv_ids_from_component += self.rdf_handler.check_indiv_for_selection(components[i][0], 'ids')

                logging.info("INDIVS LIST UPDATE: %s" % str(indiv_ids_from_component))
                    # indiv_ids_from_component += self.rdf_handler.check_indiv_for_selection(selection[i][0], 'ids')
                

        logging.info("INDIVS from component: %s" % str(indiv_ids_from_component))

        return indiv_ids_from_component, selection_filter

    # def from_selection_to_ids(self, selection):
    #     """
    #     Get all the individuals ids corresponding to the selection identified in the keywords
    #     :param selection: List of biological component identified
    #     :param properties: List of property associated
    #     :param ids: List of putative ids associated to components
    #     :return: individuals: List of ids stored in RDF
    #     """
    #     individuals = []
    #     indiv_ids_from_component = []
    #     indiv_ids_from_filter
    #     indiv_uri_from_component = []
    #     indiv_from_property = []
    #     temporary_storage = []
    #     selection_filter = []
    #     # Iterate over each component and property selection
    #     for i in range(0, len(selection)):
    #         print "**********" 
    #         print "Selection:"
    #         print selection[i]
    #         print "**********" 
    #         # COMPONENT
    #         if selection[i][1] == 'component':
    #             if i+1 < len(selection) and selection[i+1][1] == 'id':
    #                 for j in range(i+1, len(selection)):
    #                     if selection[j][1] == 'id':
    #                         # In the case where the desired output scale is equal to the component we identified
    #                         # We don't need to search for ids if it's already given by the keywords
    #                         if self.rdf_handler.scale.lower() == selection[i][0].lower():
    #                             print "Scale and component levels identical, take ids directly"
    #                             indiv_ids_from_component.append(selection[j][0])
    #                         else:
    #                             print "Scale and component levels different, check levels"
    #                             if selection[i][0] in component_hierarchical_level:
    #                                 # When a higher hierarchical lvl component is found, it can be interpreted in 2 ways:
    #                                 # 1. If alone, all of his children of the general hierarchical lvl needs to be selected
    #                                 # 2. If used with another lower hierarchical lvl, we use it as filter
    #                                 if component_hierarchical_level[selection[i][0]] > component_hierarchical_level[self.rdf_handler.scale.capitalize()]:
    #                                     print selection[i][0]+" > "+self.rdf_handler.scale
    #                                     if number_of_components > 1:
    #                                         selection_filter += selection
    #                                         break
    #                                     else:
    #                                         if selection[i][0] in aa_name_3:
    #                                             indiv_ids_from_component += self.rdf_handler.check_indiv_for_selection(aa_name_3[selection[i][0]].lower(), 'ids', selection[j][0])
    #                                         else:
    #                                             indiv_ids_from_component += self.rdf_handler.check_indiv_for_selection(selection[i][0], 'ids', selection[j][0])
    #                                 else:

    #                             # indiv_ids_from_component += self.rdf_handler.check_indiv_for_selection(aa_name_3['selection[i][0]'], 'ids', selection[j][0])
    #                     else:
    #                         break
    #             elif i+1 < len(selection) and selection[i+1][1] == 'from':
    #                 if self.rdf_handler.scale.lower() == selection[i][0].lower():
    #                     for j in range(selection[i+1][0], selection[i+2][0]+1):
    #                         indiv_ids_from_component.append(j)
    #                 else:
    #                     indiv_ids_from_component += self.rdf_handler.check_indiv_for_selection(selection[i][0], 'ids',
    #                                                                                           selection[i+1][0],
    #                                                                                           selection[i+2][0])
    #             else:
    #                 print selection[i][0]
    #                 if selection[i][0] in aa_name_3:
    #                     res = aa_name_3[selection[i][0]].lower()
    #                     indiv_ids_from_component += self.rdf_handler.check_indiv_for_selection(res, 'ids')
    #                 else:
    #                     indiv_ids_from_component += self.rdf_handler.check_indiv_for_selection(selection[i][0], 'ids')
    #                 # indiv_ids_from_component += self.rdf_handler.check_indiv_for_selection(selection[i][0], 'ids')
            

    #     print "INDIVS from component: %s" % str(indiv_ids_from_component)
        


    #     if len(indiv_from_property) > 0 and len(indiv_ids_from_component) > 0:
    #         individuals = [ind for ind in indiv_ids_from_component if ind in indiv_from_property]
    #         print individuals
    #         return individuals, selection_filter
    #     elif len(indiv_from_property) > 0:
    #         , selection_filter
    #     else:
    #         return indiv_ids_from_component, selection_filter

    @staticmethod
    def convert_to_OWL_format(keywords):
        converted = []
        for k in keywords:
            if isinstance(k, str):
                converted.append(k.capitalize())
            else:
                converted.append(k)
        return converted


if len(sys.argv) > 1:
    # Manual keywords
    keywords = sys.argv[1:]
else:
    # Send keyword command
    keywords = ['show', 'hydrophobic', 'chain', 'A', 'B', 'residue', 1,2,3,24, 'ribbon']
    #keywords = ['show', 'secondary_structure', 'residue', [2,5], 'cartoon']

print keywords
start_time = time.time()
keyword2command = Keyword2Cmd(keywords)
keyword2command.translate()
stop_time = time.time() - start_time
print("--- %s seconds ---" % stop_time)

