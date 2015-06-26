from RDFHandler.RDF_handling_distant import RDF_Handler

import logging
import sys

__author__ = 'trellet'


class Keyword2Cmd:

    def __init__(self, keywords, sub_selection=None):
        self.keywords = self.convert_to_OWL_format(keywords)
        self.rdf_handler=RDF_Handler("http://localhost:8890/sparql", "http://peptide_traj_18062015.com",
                                     "http://peptide_traj_18062015.com/rules", "my",
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
                        self.keywords.remove(l)

        # We identify each keyword type and family
        for key in self.keywords:
            # We check for id associated to the component
            if previous == 'component' and isinstance(key, list):
                if not isinstance(key[0], int) or not isinstance(key[1], int):
                    logging.error('You cannot have non integer values for a range of ids')
                selection.append((key[0], 'from'))
                selection.append((key[1], 'to'))
                previous = types[3]
            elif previous == 'id' and self.rdf_handler.is_id(key, selection[-2][0]):
                selection.append((key, 'id'))
                previous = types[5]
            elif previous == 'component' and self.rdf_handler.is_id(key, selection[-1][0]):
                selection.append((key, 'id'))
                previous = types[5]
            elif self.rdf_handler.is_action(key):
                action.append(key)
                previous = types[0]
            elif isinstance(key, str) and self.rdf_handler.is_component(key):
                selection.append((key, 'component'))
                previous = types[3]
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
        print selection
        ids = self.from_selection_to_ids(selection)

        if len(action) > 0:
            print action
            for a in action:
                require = self.rdf_handler.requirement_for_action(a)
                command += a.lower()+" "
                print require
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

        print command


    def from_selection_to_ids(self, selection):
        """
        Get all the individuals ids corresponding to the selection identified in the keywords
        :param selection: List of biological component identified
        :param property: List of property associated
        :param ids: List of putative ids associated to components
        :return: individuals: List of ids stored in RDF
        """
        individuals = []
        indiv_ids_from_component = []
        indiv_uri_from_component = []
        indiv_from_property = []
        for i in range(0, len(selection)):
            if selection[i][1] == 'component':
                if i+1 < len(selection) and selection[i+1][1] == 'id':
                    for j in range(i+1, len(selection)):
                        if selection[j][1] == 'id':
                            # In the case where the desired output scale is equal to the component we identified
                            # We don't need to search for ids if it's already given by the keywords
                            if self.rdf_handler.scale.lower() == selection[i][0].lower():
                                indiv_ids_from_component.append(selection[j][0])
                            else:
                                indiv_ids_from_component += self.rdf_handler.check_indiv_for_selection(selection[i][0], 'ids', selection[j][0])
                elif i+1 < len(selection) and selection[i+1][1] == 'from':
                    if self.rdf_handler.scale.lower() == selection[i][0].lower():
                        for j in range(selection[i+1][0], selection[i+2][0]+1):
                            indiv_ids_from_component.append(j)
                    else:
                        indiv_ids_from_component += self.rdf_handler.check_indiv_for_selection(selection[i][0], 'ids',
                                                                                              selection[i+1][0],
                                                                                              selection[i+2][0])
                else:
                    indiv_ids_from_component += self.rdf_handler.check_indiv_for_selection(selection[i][0], 'ids')
            elif selection[i][1] == 'property':
                indiv_from_property += self.rdf_handler.check_indiv_for_property(selection[i][0])
                print indiv_from_property
                indivs_set = set(indiv_from_property)
                print indivs_set
                indiv_from_property = list(indivs_set)
                print indiv_from_property

        print "INDIVS from component: %s" % str(indiv_ids_from_component)
        print "INDIVS from property: %s" % str(indiv_from_property)


        if len(indiv_from_property) > 0 and len(indiv_ids_from_component) > 0:
            individuals = [ind for ind in indiv_ids_from_component if ind in indiv_from_property]
            print individuals
            return individuals
        elif len(indiv_from_property) > 0:
            return indiv_from_property
        else:
            return indiv_ids_from_component

    @staticmethod
    def convert_to_OWL_format(keywords):
        converted = []
        for k in keywords:
            if isinstance(k, str):
                converted.append(k.capitalize())
            else:
                converted.append(k)
        return converted

