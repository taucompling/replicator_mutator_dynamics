import numpy as np

def normalize_cost(cost_dict, states):
    """
    cost = max(cost) - cost +1 and then normalize it
    :param cost_dict: dictionary with costs for messages
    :type cost_dict: dict
    :param states: number of states
    :type: list
    :return: dictionary with normalized costs
    :rtype: dictionary
    """
    k_length_cost = {}
    for key, value in cost_dict.items():
        try:
            k_length_cost[len(key)].append(value)
        except KeyError:
            k_length_cost[len(key)] = [value]

    if states not in k_length_cost:
        raise Exception(f"No cost function defined for {state} states. Add it in lexica.py in get_prior().")
    
    for key, value in cost_dict.items():
        cost_dict[key] = (max(k_length_cost[len(key)]) - value + 1)/np.sum(k_length_cost[len(key)])

    return cost_dict

def calculate_cost_dict(cost, states, puzzle):
    """Calculates prior over lexicon

    :param lexica_list: list of lexica
    :type lexica_list: list of lists
    :return: list of priors for each lexicon
    :rtype: list
    """
 
    if cost == "brochhagen": # cost of each concept in 'concepts'
        cost_dict = {(0,0,1): 3, (0,1,0):8, (0,1,1):4, (1,0,0):4, (1,0,1):10, (1,1,0):5, # for three states
                    (0,1):3, (1,0):4}  # for two states
    elif cost == "building_blocks":
        cost_dict = {(0,0,1): 8, (0,1,0): 21, (0,1,1): 8, (1,0,0): 7, (1,0,1): 18, (1,1,0): 10, # for three states
                    (0,1):8, (1,0):7}  # for two states
    
    elif cost == "equal":
        cost_dict = {(0,0,1): 1, (0,1,0): 1, (0,1,1): 1, (1,0,0): 1, (1,0,1): 1, (1,1,0): 1, # for three states
            (0,1):1, (1,0):1}  # for two states

    elif cost == "sonstiges":

        cost_dict = {(0,0,1): 1, (0,1,1): 1, (1,1,0):8, (1,0,0): 1,  # 4 corners
                    (1,0, 1): 20, (0,1,0): 20, # high
                    (0,1):1, (1,0):1}  # for two states
    else:
        raise Exception("Cost function is not defined. Please define it in lexica.py")


    if puzzle:
        del cost_dict[(1, 0, 1)]
        del cost_dict[(0, 1, 0)]

    cost_dict = normalize_cost(cost_dict, states)
    return cost_dict