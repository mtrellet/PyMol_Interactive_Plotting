from RDFHandler.RDF_handling_distant import RDF_Handler

__author__ = 'trellet'


class Keyword2Cmd:

    def __init__(self, keywords, sub_selection=None):
        self.keywords = self.convert_to_OWL_format(keywords)
        self.rdf_handler=RDF_Handler("http://localhost:8890/sparql", "http://peptide_traj.com", "http://peptide_traj.com/rules", "my", "http://www.semanticweb.org/trellet/ontologies/2015/0/VisualAnalytics#")
        self.sub_selection = sub_selection

    def translate(self):
        action = []
        representation = []
        color = []
        selection = []
        types = ['action', 'representation', 'color', 'component', 'property', 'id']
        command = dict.fromkeys(types)
        ids = 0
        previous = None
        for key in self.keywords:
            # We check for id associated to the component
            if previous == 'component':
                if self.rdf_handler.is_id(key, selection[-1][0]):
                    selection.append((key, 'id'))
                    ids += 1;
                    previous = types[5]
            else:
                if self.rdf_handler.is_action(key):
                    action.append(key)
                    previous = types[0]
                elif self.rdf_handler.is_component(key):
                    selection.append((key, 'component'))
                    previous = types[3]
                # elif self.rdf_handler.is_id(key):
                #     selection.append((key, 'id'))
                #     ids += 1;
                #     previous = types[5]
                elif self.rdf_handler.is_representation(key):
                    representation.append(key)
                    previous = types[1]
                elif self.rdf_handler.is_color(key):
                    color.append(key)
                    previous = types[2]
                elif self.rdf_handler.is_property(key):
                    selection.append(key, 'property')
                    previous = types[4]
        print action
        if selection:
            print selection
            command['selection'] = self.from_selection_to_ids(selection, property, ids)

    def from_selection_to_ids(self, selection, property, ids):
        """
        Get all the individuals ids corresponding to the selection identified in the keywords
        :param selection: List of biological component identified
        :param property: List of property associated
        :param ids: List of putative ids associated to components
        :return: individuals: List of ids stored in RDF
        """
        individuals = []
        indiv_from_object_id_pair = []
        if ids > 0:
            for i in range(0, len(selection)):
                if selection[i][1] == 'component':
                    if selection[i+1][1] == 'id' or selection[i+1][1] == 'property':
                        indiv_from_object_id_pair = self.rdf_handler.check_indiv_for_selection(selection[i], selection[i+1])
                    if len(indiv_from_object_id_pair) > 0:
                        return individuals
        return individuals

    @staticmethod
    def convert_to_OWL_format(keywords):
        converted = []
        for k in keywords:
            if isinstance(k, str):
                converted.append(k.capitalize())
            else:
                converted.append(k)
        return converted

