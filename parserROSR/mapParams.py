from datetime import datetime

def object_type(type):
    if type == '002001001000':
        return 'Земельный участок'
    elif type == '002001002000':
        return 'Здание'
    elif type == '002001003000':
        return 'Помещение'
    else:
        return None
    

def rights(rights):

    str = ''

    for right in rights:
        str += '['
        str +=right['rightTypeDesc'] + ', '
        str += right['rightNumber'] + ', '
        str += datetime.fromtimestamp(right['rightRegDate'] / 1000).strftime('%Y-%m-%d')
        str += '], '
    str = str[:-2]
    return str

def old_numbers(old_numbers):
    str = ''
    for num in old_numbers:
        str = ''
        str += '['
        str += num['numType'] + ', '
        str += num['numValue']
        str += '], '
    str = str[:-2]
    return str

def main_characters(main_characters):
    string = ''
    for char in main_characters:
        string += '['
        string += char['code'] + ', '
        string += char['description'] + ', '
        string += str(char['value']) + ', '
        string += char['unitCode'] + ', '
        string += char['unitDescription']
        string += '], '
    string = string[:-2]
    return string


def structure_keys():
    return {
    'cadnum': 'Не найдено',
    'pretty_address': None,
    'type': None,
    "objectId": None,
    "databaseName": None,
    "regionKey": None,
    "cadNumber": None,
    "cadQuarter": None,
    "status": None,
    "objType": None,
    "area": None,
    "address": None,
    "regDate": None,
    "cancelDate": None,
    "rights": None,
    "encumbrances": None,
    "oldNumbers": None,
    "landCategory": None,
    "permittedUse": None,
    "permittedUseByDoc": None,
    "cadCost": None,
    "cadCostDate": None,
    "cadCostDeterminationDate": None,
    "cadCostRegistrationDate": None,
    "infoUpdateDate": None,
    "cadEngFIO": None,
    "cadEngCertNumber": None,
    "cadEngPhone": None,
    "floor": None,
    "undergroundFloor": None,
    "levelFloor": None,
    "ownershipType": None,
    "oksWallMaterial": None,
    "oksCommisioningYear": None,
    "oksYearBuild": None,
    "purpose": None,
    "childCadNumbers": None,
    "parentCadNumber": None,
    "mainCharacters": None
}
