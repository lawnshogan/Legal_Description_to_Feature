'''
'''
import re
from typing import Dict, List, Tuple

import ld_patterns

#<<<<<<<<<<<<<<<     >>>>>>>>>>>>>>>
EXCEPTIONS_FOR_ALLS = [
    'except',
    'execpt',
    ' exc ',
    'fp ',
    'fraction',
    'less',
    'lot',
    'lying',
    'parts',
    'tract'
]


#<<<<<<<<<<<<<<<     >>>>>>>>>>>>>>>
def _has_exceptions_in_alls(str_to_check:str) -> bool:
    '''
    Return true if one of the exceptions is present and the
    text contains 'all'
    '''
    test_results = False

    if isinstance(str_to_check, str):
        test_str_lower = str_to_check.lower()

    if str_to_check is None:
        test_results = False
    elif len(str_to_check) == 0:
        test_results = False


    if 'all' in test_str_lower.lower():
        for exception in EXCEPTIONS_FOR_ALLS:
            if exception in test_str_lower:
                test_results = True
                break
    else:
        test_results = False

    return test_results


def _check_for_all_values(test_str:str) -> bool:
    '''
    Test if the string qualifies as an 'all' or not
    '''


    if isinstance(test_str, str):
        test_str_lower = test_str.lower()

    # Assumes if an empty value is sent, the source data did not specific anything specific
    if test_str is None:
        test_results = True
    elif len(test_str) == 0:
        test_results = True

    # Test the string now verified as present
    elif test_str_lower.strip() == 'all':
        test_results = True
    elif 'all ' not in test_str_lower:
        test_results = False
    else:
        if _has_exceptions_in_alls(test_str_lower):
            test_results = False
        else:
            test_results = True

    return test_results


def _known_pattern_search(test_str:str) -> Tuple[str, List[str]]:
    '''
    '''
    found_patterns = []
    return_string = test_str

    for word in ld_patterns.PATTERNS.keys():
        if word in test_str:
            r_key_check = re.compile(rf'\b{word}\b')
            results = r_key_check.findall(test_str)

            if results:
                found_patterns.append(word)
                return_string = r_key_check.sub('', return_string)

    return (return_string, found_patterns)


def _lot_list_search(test_str:str) -> Tuple[str, List[str]]:
    '''
    '''
    found_patterns = []
    return_string = test_str

    r_lot_list = re.compile(r'\d+-\d+')

    results = r_lot_list.findall(test_str)
    for item in results:
        item_split = item.split('-')
        lot_list = list(range(int(item_split[0]), int(item_split[1])+1))
        found_patterns.extend(lot_list)
    return_string = r_lot_list.sub('', test_str)

    return (return_string, found_patterns)


def _evaluate_remaining_words(test_str:str) -> Tuple[List[str], List[str], List[str]]:
    '''
    '''
    found_patterns = []
    lot_numbers = []
    fall_out_words = []

    r_word_list = re.compile(r'\w+')

    results = r_word_list.findall(test_str)

    for word in results:
        if word.isdigit():
            lot_numbers.append(int(word))
        elif word in ld_patterns.PATTERNS.keys():
            found_patterns.append(word)
        else:
            fall_out_words.append(word)

    return (lot_numbers, found_patterns, fall_out_words)


def _fractional_pattern_search(test_str:str) -> Tuple[str, List[str]]:
    '''
    '''
    found_patterns = []
    return_string = test_str

    r_fractional = re.compile(r'[NSEW]+[1]\/[2,4]')

    results = r_fractional.findall(test_str)
    found_patterns.extend(results)
    return_string = r_fractional.sub('', test_str)

    return (return_string, found_patterns)


def _parse_for_search_items(test_str:str) -> Dict[str, list]:
    '''
    '''
    lookup_batch = []
    lot_number_batch = []
    fractional_batch = []
    fall_out_batch = []

    new_str = test_str

    if '½' in new_str:
        new_str = new_str.replace('½', '1/2')
    if '¼' in new_str:
        new_str = new_str.replace('¼', '1/4')


    # Searching for patterns that have already been identified
    lookup_results = _known_pattern_search(new_str)
    new_str = lookup_results[0]
    lookup_batch.extend(lookup_results[1])


    # Looks for lookup strings with the format like 'NE1/4', etc.
    # Drop into the fractional batch for review
    fractional_results = _fractional_pattern_search(new_str)
    new_str = fractional_results[0]
    fractional_batch.extend(fractional_results[1])


    # Looks for strings like '1-4', lot/track numbers
    lot_list_results = _lot_list_search(new_str)
    new_str = lot_list_results[0]
    lot_number_batch.extend(lot_list_results[1])



    # Divides the remaining string up into word size chunks to evaluate
    remaining_results = _evaluate_remaining_words(new_str)
    lot_number_batch.extend(remaining_results[0])
    lookup_batch.extend(remaining_results[1])
    fall_out_batch.extend(remaining_results[2])


    return {
            'lookups': lookup_batch,
            'lots': lot_number_batch,
            'fractionals': fractional_batch,
            'fall_outs': fall_out_batch
            }


def get_2nd_div(search_str:str) -> dict:
    '''
    Parse the legal description from Netsuite.

    Dictionary returned provides a list of lookups ('ALL' if
    full section), a list of fractional outputs that could not
    be parsed, and a list of fall outs that do not fit the
    established patterns.
'''
    results = {
        'lookups': [],
        'fractionals': [],
        'fall_outs': []
        }

    if _check_for_all_values(search_str):
        results['lookups'] = ['ALL']
        return results

    # Need to exclude the 'all excepts' from the 2nd div search/parsing
    if _has_exceptions_in_alls(search_str):
        raise ValueError('Unable to parse 2nd Division number for this Legal Description')

    search_results = _parse_for_search_items(search_str)

    lookup_list = []

    results['fractionals'] = search_results['fractionals']
    results['fall_outs'] = search_results['fall_outs']

    if len(search_results['lookups']) > 0:
        for lookup_key in search_results['lookups']:
            lookup_list.extend(ld_patterns.PATTERNS[lookup_key])

    for lot_num in search_results['lots']:
        lookup_list.append(str(lot_num))

    # Creating a set to remove duplicates, then casting as a list
    results['lookups'] = list({item for item in lookup_list if item is not None and len(item) > 0})

    if len(results['lookups']) == 0:
        raise ValueError('Unable to parse 2nd Division number for this Legal Description')

    return results
