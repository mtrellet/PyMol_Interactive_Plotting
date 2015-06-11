from RDFHandler.RDF_handling_distant import RDF_Handler

__author__ = 'trellet'


class Keyword2Cmd:

    def __init__(self, keywords, sub_selection):
        self.keywords = self.convert_to_OWL_format(keywords)
        self.rdf_handler=RDF_Handler("http://localhost:8890/sparql", "http://peptide_traj.com", "http://peptide_traj.com/rules", "my", "http://www.semanticweb.org/trellet/ontologies/2015/0/VisualAnalytics#")
        self.sub_selection = sub_selection

    def translate(self):
        action = []
        representation = []
        color = []
        selection = []
        property = []
        command = dict.fromkeys(['action', 'representation', 'color', 'selection', 'property'])
        ids = 0
        for key in self.keywords:
            if self.rdf_handler.is_action(key):
                action.append(key)
            elif self.rdf_handler.is_selection(key):
                selection.append((key, 'component'))
            elif self.rdf_handler.is_id(key):
                selection.append((key, 'component'))
                ids += 1;
            elif self.rdf_handler.is_representation(key):
                representation.append(key)
            elif self.rdf_handler.is_color(key):
                color.append(key)
            elif self.rdf_handler.is_property(key):
                property.append(key)

        if selection:
            command['selection'] = self.from_selection_to_ids(selection, property, ids)

    def from_selection_to_ids(self, selection, property, ids):
        groups = []
        indiv_from_object_id_pair = []
        if ids > 0:
            for i in range(0, len(selection)):
                if (selection[i][1] == 'component') and (selection[i+1][1] == 'id'):
                    indiv_from_object_id_pair = self.rdf_handler.check_indiv_for_selection(selection[i][0], selection[i+1][0])
                    if len(indiv_from_object_id_pair) > 0:
                        return []
        return []

    @staticmethod
    def convert_to_OWL_format(self, keywords):
        return [key.capitalize() for key in keywords]

