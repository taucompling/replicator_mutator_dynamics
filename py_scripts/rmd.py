## Functions for replicator-mutator dynamics with iterated learning as mutator dynamics

import numpy as np
#np.set_printoptions(threshold=np.nan)
from random import sample
from itertools import product
from collections import defaultdict
from tqdm import tqdm

from py_scripts.player import LiteralPlayer,GriceanPlayer
from py_scripts.lexica import get_lexica,get_prior,get_lexica_bins
from py_scripts.process_predefined_lexica import  get_predefined_lexica
from py_scripts.mutation_matrix import summarize_counts, get_obs, get_mutation_matrix, get_likelihood
from py_scripts.mutual_utility import get_utils
from py_scripts.message_costs import calculate_cost_dict
from py_scripts.plots.plot_progress import plot_progress
from py_scripts.plots.plot_all_sizes import plot_all_sizes
from py_scripts.plots.x_best_prag_lit import print_best_x_types_to_file
from py_scripts.plots.proportion_target_types import get_target_types
import sys 
import datetime
import csv
import os.path
from fractions import Fraction

def get_type_bin(type_idx, bins):

    for b in range(len(bins)):
        if type_idx in bins[b]:
            return b
    raise Exception("Something did not work out with the bins!")

def get_lexica_representations(type, lexica, puzzle):
    l = lexica[type-len(lexica)]
    for column in l.T:
        if -5 in column:
            l = np.delete(l, np.where(l == -5)[1][0], 1)
    return f"{check_literal_or_pragmatic(type, lexica, puzzle)}:\n{l}"

def check_literal_or_pragmatic(type, lexica, puzzle):
    if type > len(lexica)-1 or puzzle:
        return "pragmatic"
    return "literal"

def get_target_bins(type_idx, bins, level, number_of_lexica, puzzle):
    target_bins = []
    for l in level:
        if l == "literal" or puzzle:
            target_bins.append(get_type_bin(type_idx, bins))
        else:
            target_bins.append(get_type_bin(type_idx + number_of_lexica, bins))
    return target_bins

def conv_frac(s):
    """
    converts fraction string to float

    """
    return float(sum(Fraction(x) for x in s.split()))

def run_dynamics(alpha,lam,k,sample_amount,gens,runs,learning_parameter,kind,mutual_exclusivity, result_path, 
                cost, target_lex, target_level, competitor_lex, competitor_level, predefined = False, states=0, messages=0, 
                print_x=6, puzzle = False, negation_rate=False, utility_message_cost=False, state_priors=False):

    """[Runs the replicator mutator dynamics
    :param alpha: rate to control difference between semantic and pragmatic violations
    :type alpha: int
    :param lam: softmax parameter
    :type lam: int
    :param k: sequence length
    :type k: int
    :param sample_amount: amount of samples (how many sequences)
    :type sample_amount: int
    :param gens: number of generations per simulation run
    :type gens: int
    :param runs: number of independent simulation runs
    :type runs: int
    :param learning_parameter: prob-matching = 1, increments approach MAP
    :type learning_parameter: int
    :param kind: model type (r (replicator), m (mutator), rmd)
    :type kind: string
    :param mutual_exclusivity: no concept assigned to more than one message
    :type mutual_exclusivity: boolean
    :param result_path: path to store results
    :type string
    :cost: type of cost function for the messages 
    :type: string
    :param target_lex: lexicon of target type
    :type: list
    :param target_level: level of target type (literal or pragmatic)
    :type: list
    :param competitor_lex: lexicon of competitor type
    :type: list
    :param competitor_level: level of competitor type (literal or pragmatic)
    :type: list
    :param predefined: Path to predefined lexica, else False
    :type: string or boolean
    :param states: amount of states
    :type states: int
    :param messages: amount of messages
    :type messages: int
    :param print_x: number of best x types to print in the results
    :type: int
    :state_priors: different priors over states
    :type: list
    :puzzle: only allow the 4 corneres from the typological puzzle and pragmatic players
    :type: boolean (default false)
    """
 
    print('# Starting,\t\t\t', datetime.datetime.now().replace(microsecond=0))
    if not os.path.isdir("experiments/" + result_path):
        os.makedirs("experiments/" + result_path)

    all_messages = messages

    if predefined: 
        lexica, target_index, competitor_index, states, all_messages = get_predefined_lexica(predefined, target_lex, competitor_lex)
        state_priors = np.array([conv_frac(sp) if type(sp) == str else sp for sp in state_priors  ])

    else: 
        if not state_priors:
            state_priors = np.ones(states) / float(states)
        else:
            state_priors = np.array([conv_frac(sp) if type(sp) == str else sp for sp in state_priors  ])
            if state_priors.shape[0] != states:
                raise Exception(f"State priors don't fit the amount of states ({states})")

            if round(np.sum(state_priors), 6) != 1:
                raise Exception(f"State priors dont' sum up to 1.")

        if print_x > 0:
            if len(target_lex[0]) not in all_messages or len(target_lex) != states:
                raise Exception("Target type does not fit the number of states and messages!")
            if len(competitor_lex[0]) not in all_messages or len(competitor_lex)  != states:
                raise Exception("Competitor type does not fit the number of states and messages!")

        lexica, target_index, competitor_index = [], [], []
        for message in all_messages:
            lexicon, target_in, competitor_in = get_lexica(states, message, max(all_messages), target_lex, competitor_lex, mutual_exclusivity, puzzle)
            lex_len = len(lexica)
            lexica += lexicon
            target_index += [lex_len + t for t in target_in]
            competitor_index += [lex_len + t for t in competitor_in]

    bins = get_lexica_bins(lexica, states, puzzle) #To bin types with identical lexica
    target_bins = get_target_bins(target_index[0], bins, target_level, len(lexica), puzzle) if print_x > 0 else None

    competitor_bins = get_target_bins(competitor_index[0], bins, competitor_level, len(lexica), puzzle) if print_x > 0 else None

    message_costs = calculate_cost_dict(cost, states, puzzle)   
    l_prior = get_prior(lexica, puzzle, message_costs) 

    if puzzle:
        typeList = [GriceanPlayer(alpha,lam,lex, state_priors, message_costs) for lex in lexica]
    else:
        typeList = [LiteralPlayer(lam,lex, state_priors) for lex in lexica] + [GriceanPlayer(alpha,lam,lex, state_priors) for lex in lexica]
        
    u = get_utils(typeList, all_messages, states, lam,alpha,mutual_exclusivity, result_path, predefined, state_priors, utility_message_cost)

    if kind == "rmd" or kind == "m":
        q = get_mutation_matrix(states, all_messages, typeList,l_prior,learning_parameter,sample_amount,k,lam,alpha,mutual_exclusivity, result_path, predefined, state_priors, negation_rate)
    
    print('# Beginning multiple runs,\t', datetime.datetime.now().replace(microsecond=0))

    if not os.path.isdir("experiments/" + result_path + "/results/"):
        os.makedirs("experiments/" + result_path + "/" +"results/")
   
    f = csv.writer(open(f'experiments/{result_path}/results/{kind}-{state_priors}-s{states}-m{all_messages}-lam{lam}-a{alpha}-k{k}-samples{sample_amount}-l{learning_parameter}-g{gens}-me{mutual_exclusivity}-sp{state_priors}-puzzle{puzzle}.csv','w'))

    f.writerow(['runID','kind']+['t_ini'+str(x) for x in range(len(typeList))] +\
               ['lam', 'alpha','k','samples','l','gens', 'm_excl'] + ['t_final'+str(x) for x in range(len(typeList))])
    

    if os.path.isfile('experiments/%s/results/00mean-%s-%s-s%s-m%s-g%d-r%d-me%s.csv' %(result_path, kind, str(state_priors),str(states),str(all_messages),gens,runs,str(mutual_exclusivity))):
        f_mean = csv.writer(open('experiments/%s/results/00mean-%s-%s-s%s-m%s-g%d-r%d-me%s.csv' %(result_path, kind, str(state_priors),str(states),str(all_messages),gens,runs,str(mutual_exclusivity)), 'w'))
    else: 
        f_mean = csv.writer(open('experiments/%s/results/00mean-%s-%s-s%s-m%s-g%d-r%d-me%s.csv' %(result_path, kind, str(state_priors), str(states),str(all_messages),gens,runs,str(mutual_exclusivity)), 'w'))
        f_mean.writerow(['kind','lam','alpha','k','samples','l','gens','runs','m_excl'] + ['t_mean'+str(x) for x in range(len(typeList))])
       

    p_sum = np.zeros(len(typeList)) #vector to store mean across runs
    


    gen_winners = [[None], 0]
    avg_gens = []

    

    bin_orders = defaultdict(lambda: [0,0])
    all_progress = []

    
    for i in tqdm(range(runs)):
        progress = []
        p = np.random.dirichlet(np.ones(len(typeList))) # unbiased random starting state
        #p = np.random.uniform(np.ones(len(typeList)))
        p_initial = p
        r = 0
        while True:

            #print("GENERATION: ", r+1)
            #print(p)

            if kind == 'rmd':
                pPrime = p * [np.sum(u[t,] * p)  for t in range(len(typeList))] # type_prob * fitness
                pPrime = pPrime / np.sum(pPrime) # / average fitness in population 
                p = np.dot(pPrime, q) # * Q-matrix

            elif kind == 'm': # learnability
                p = np.dot(p,q) # without fitness

            elif kind == 'r': # communicative success
                pPrime = p * [np.sum(u[t,] * p)  for t in range(len(typeList))] # without mutation matrix
                p = pPrime / np.sum(pPrime)

            

            progress.append(p)

            #late stopping

            #print(len(p))
            #print(len(typeList))
            #raise Exception
            gen_winner = np.argpartition(p, -print_x)[-print_x:] # ascending order
            sorted_gen_winner = np.flip(gen_winner[np.argsort(p[gen_winner])]) # descending order
            sorted_gen_winner_tuples = [(winner, round(p[winner], 10)) for winner in sorted_gen_winner]
            
            if np.array_equal(sorted_gen_winner_tuples, gen_winners[0]):
                gen_winners[1] +=1
            else:
                gen_winners[0], gen_winners[1] = sorted_gen_winner_tuples, 1
            
            if r >= gens and gen_winners[1] >= 10:
                avg_gens.append(r)
                break
            
            if r == 20000:
                avg_gens.append(r)
                print("STOPPED after 20000 generations")
                break

            r+=1

        all_progress.append(progress) 

        f.writerow([str(i),kind] + [str(p_initial[x]) for x in range(len(typeList))]+\
                   [str(lam),str(alpha),str(k),str(sample_amount),str(learning_parameter),str(gens),str(mutual_exclusivity)] +\
                   [str(p[x]) for x in range(len(typeList))])
        p_sum += p
        
        # Track Winner Bin
        bin_orders[tuple(bins[get_type_bin(np.argmax(p), bins)])][0] += max(p)
        bin_orders[tuple(bins[get_type_bin(np.argmax(p), bins)])][1] += 1


    
    

    gens = np.average(avg_gens)
    p_mean = p_sum / runs 
    f_mean.writerow([kind,str(lam),str(alpha),str(k),str(sample_amount),str(learning_parameter),str(gens),str(runs),str(mutual_exclusivity)] +\
                        [str(p_mean[x]) for x in range(len(typeList))])
    
    
    inc = np.argmax(p_mean)
    best_x = np.argpartition(p_mean, -print_x)[-print_x:] if print_x > 0 else np.argpartition(p_mean, -10)[-10:] # ascending order

    sorted_best_x = np.flip(best_x[np.argsort(p_mean[best_x])]) #descending order

    inc_bin = get_type_bin(inc,bins)

    sum_winning_types = 0

    for inc_bin_type in bins[inc_bin]:

        sum_winning_types += p_mean[inc_bin_type]

    bin_winner = max(bin_orders, key=lambda k: bin_orders[k][1])

    if print_x > 0:
        plot_all_sizes(progress, print_x, result_path, lexica, puzzle)
        #plot_progress(progress, print_x, result_path, lexica, puzzle)          
        if not puzzle:
            pragmatic_vs_literal(progress, p_mean, lexica, result_path, print_x)        
        print_best_x_types_to_file(p_mean, lexica,result_path, print_x)
        average_best = round(bin_orders[bin_winner][0]/bin_orders[bin_winner][1],4)
        #get_target_types(average_best, bins, target_bins, competitor_bins, all_progress, result_path)

    #print(target_bins)
    #print(target_bins[0])
    #print(get_lexica_representations(target_bins[0], lexica, puzzle))
    #print(bins[target_bins[0]])
    #print(bin_orders)

    end_results = [
    "-------------------------------------------------------------------------------------------------------------------------------------------------\n", 
    '*** Results with parameters: dynamics= %s, alpha = %d, lambda = %d, k = %d, samples per type = %d, learning parameter = %.2f, avg_generations = %d, runs = %d ***\n' % (kind, alpha, lam, k, sample_amount, learning_parameter, gens, runs),
    f"*** Lexica parameters: states={states}, messages={all_messages}, cost={cost}, state priors = {state_priors}, puzzle = {puzzle}***\n",
    "-------------------------------------------------------------------------------------------------------------------------------------------------\n",     
    f"# WINNER BIN in {round(bin_orders[bin_winner][1]/runs * 100,2)} percent of the runs:\n",
    f"# Average Proportion: {round(bin_orders[bin_winner][0]/bin_orders[bin_winner][1],4)}\n",
    f"{get_lexica_representations(bin_winner[0], lexica, puzzle)}\n",    
    "-------------------------------------------------------------------------------------------------------------------------------------------------\n",    
    #f"# Incumbent type: {inc} with proportion {p_mean[inc]}\n",
    #f"{get_lexica_representations(inc, lexica, puzzle)}\n",
    #f"# The bin of the incumbent {inc_bin}\n",
    #f"# Bin: {bins[inc_bin]}\n",
    f"# Summed proportion of the bin of the incumbent: {round(sum_winning_types,4)}\n",
    "-------------------------------------------------------------------------------------------------------------------------------------------------\n",    
    f"# {print_x if print_x > 0 else 10} best types: \n"]
    for typ in sorted_best_x:
        end_results.append(f"-Type {typ} with proportion {p_mean[typ]}\n")
        end_results.append(f"{(get_lexica_representations(typ, lexica, puzzle))}\n")
    # print("# All bins:", bins)
    
    print("# Finished:\t\t\t", datetime.datetime.now().replace(microsecond=0))
    for line in end_results:
        print(line)
    with open(f"experiments/{result_path}/results/end_results.txt", "w") as end:
        end.writelines(end_results)

    #os.system("rm -rf experiments/")