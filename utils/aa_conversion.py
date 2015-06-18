__author__ = 'trellet'

from color_by_residue import aa_1_3, aa_3_1

aa_name_3 = {
  'Alanine': 'ALA',
  'Cysteine': 'CYS',
  'Aspartate': 'ASP',
  'Glutamate': 'GLU',
  'Phenylalanine': 'PHE',
  'Glycine': 'GLY',
  'Histidine': 'HIS',
  'Isoleucine': 'ILE',
  'Lysine': 'LYS',
  'Leucine': 'LEU',
  'Methionine': 'MET',
  'asparagine': 'ASN',
  'Proline': 'PRO',
  'Glutamine': 'GLN',
  'Arginine': 'ARG',
  'Serine': 'SER',
  'Tthreonine': 'THR',
  'Valine': 'VAL',
  'Tryptophane': 'TRP',
  'Tyrosine': 'TYR',
}

atom = ["C","H","N","N","O","S"]

def from_1_to_3_letters(letter):
    try:
        return aa_1_3[letter].lower()
    except KeyError:
        return False

def from_3_to_1_letter(letters):
    try:
        return aa_3_1[letters.upper()]
    except KeyError:
        return False

def from_name_to_3_letters(name):
    try:
        return aa_name_3[name].lower()
    except KeyError:
        return False

def from_3_to_name(letters):
    for key, val in aa_name_3.iteritems():
        if val.upper() == letters:
            return key
    return False
