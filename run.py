#! /usr/bin/python3

# Copyright (c) University of Luxembourg 2020.
# Developed by Sergei Tikhomirov (sergey.s.tikhomirov@gmail.com), SnT Cryptolux group.

'''
	Run a probing experiment.

	Mode 1: single randomly-generated hops.
	This allows us to measure the effects of the optimal amount-selection strategy.
	We expect the final information gain to be very close, 
	  and the number of probes to be smaller for the optimal strategy.
	How large is the advantage - depends on hop parameters.
	For 1-channel hops, both information gain and the number of probes should be exactly the same.
	A channel with capacity 2**X in a 1-channel hop always takes X probes to fully probe.

	Mode 2: snapshot-based. Choose num_hops random target hops and probe them.
	Accounts for path-finding, accumulates information on intermediary hops as well.

	Usage example:	./run.py --num_hops=100 --use_snapshot
'''

from prober import Prober
from hop import Hop

import random
import argparse

def generate_hop(min_N, max_N, min_capacity, max_capacity, probability_enabled, balances=None):
	'''
		Generate a random hop.

		Parameters:
		- min_N: minimum number of channels
		- max_N: maximum number of channels
		- min_capacity: minimum capacity of one channel
		- max_capacity: maximum capacity of one channel
		- probability_enabled: probability that a channel is enabled in a given direction
		- balances: channel balances (generated randomly if None)

		Return:
		- a Hop instance
	'''
	N = random.randint(min_N, max_N)
	capacities = [random.randint(min_capacity, max_capacity) for _ in range(N)]
	# avoid generating hops disabled in both directions (we can't probe them anyway)
	enabled_in_one_direction = False
	while not enabled_in_one_direction:
		enabled_dir0 = [i for i in range(N) if random.random() < probability_enabled]
		enabled_dir1 = [i for i in range(N) if random.random() < probability_enabled]
		enabled_in_one_direction = enabled_dir0 or enabled_dir0
	#print("Generating hop: capacities", capacities, "enabled_dir0", enabled_dir0, "enabled_dir1", enabled_dir1)
	return Hop(capacities, enabled_dir0, enabled_dir1, balances)


def generate_hops(num_hops, max_N, max_capacity, probability_enabled, all_max):
	'''
		Generate num_hops random hops.

		Parameters:
		- num_hops: the number of hops to generate
		- max_N: maximum number of channel per hop
		- max_capacity: maximum capacity per channel
		- probability_enabled: probability that a channel is enabled in a given direction
		- all_max: if True, minimal N and capacity = max values; if False, both equal 1

		Return:
		- a list of generated hops
	'''
	if all_max:
		return [generate_hop(max_N, max_N, max_capacity, max_capacity, probability_enabled) for _ in range(num_hops)]
	else:
		return [generate_hop(1, max_N, 1, max_capacity, probability_enabled) for _ in range(num_hops)]


def probe_single_hop(hop, naive, target_uncertainty_share=0):
	'''
		Do a series of probes until the hop is fully probed.

		Parameters:
		- hop: a Hop to probe
		- naive:
		  if True: use naive amounts (divide interval between bounds on h / g in half)
		  if False: use optimal amounts (divide S(F) in half)
		- target_uncertainty_share: stop if remaining uncertainty is less than this
		  (by default, probe until uncertainty is zero)

		 Return:
		 - probes: the number of probes performed
		 - information_gain: the share of initial uncertainty resolved
	'''
	initial_uncertainty = hop.uncertainty
	assert(initial_uncertainty > 0), str(initial_uncertainty) + "\n" + str(hop)
	probes = 0
	while (hop.h_u - hop.h_l > 1 and hop.g_u - hop.g_l > 1):
		chosen_dir0 = hop.next_dir()
		amount = hop.next_a(is_dir0 = chosen_dir0, naive=naive)
		hop.probe(is_dir0=chosen_dir0, amount=amount)
		probes += 1
		current_uncertainty = hop.uncertainty
		current_uncertainty_share = current_uncertainty / initial_uncertainty
		if current_uncertainty_share  < target_uncertainty_share:
			#print("\n----------\nTarget reached: current uncertainty share = ", current_uncertainty_share)
			break
	final_uncertainty = hop.uncertainty
	final_uncertainty_share = final_uncertainty / initial_uncertainty
	information_gain = 1 - final_uncertainty_share
	return probes, information_gain


def probe_synthetic_hops(hops, naive):
	'''
		Probe each hop from a list of hops.

		Parameters:
		- hops: a list of Hops to probe
		- naive: use naive (True) or optimal (False) method

		Return:
		- probes: number of probes for each hop
		- gains: information gain for each hop
	'''
	for hop in hops:
		hop.reset()
	probes, gains = [], []
	for hop in hops:
		num_probes, gain = probe_single_hop(hop, naive=naive)
		probes.append(num_probes)
		gains.append(gain)
	#print("\nProbed with method:", "naive" if naive else "optimal")
	#print("Total gain:		", round(sum(gains),2), "after", sum(probes), "probes")
	#print("Average per hop:	", round(sum(gains)/len(gains),2), "after", sum(probes)/len(probes), "probes")
	return probes, gains


def run_experiment_synthetic(num_hops, capacity, num_channels, probability_enabled):
	'''
		Run experiment on synthetic hops.
	'''
	hops = generate_hops(num_hops, num_channels, capacity, probability_enabled, all_max=True)
	probes_naive, gains_naive 		= probe_synthetic_hops(hops, naive=True)
	probes_optimal, gains_optimal 	= probe_synthetic_hops(hops, naive=False)
	# the gain is ~ the same, could as well return naive gain
	avg_achieved_gain = sum(gains_optimal)/len(gains_optimal)
	print("Achieved average gain (optimal - naive is close):	", 
		round(100*sum(gains_optimal)/len(gains_optimal)), "%" )
	probes_decrease = (sum(probes_naive) - sum(probes_optimal)) / sum(probes_naive)
	print("Optimal algorithm decreases the number of probes by	", 
		round(100*probes_decrease), "%" )
	gains_increase = (sum(gains_optimal) - sum(gains_naive)) / sum(gains_optimal)
	print("Optimal algorithm increases information gain by		", 
		round(100*(gains_increase)), "%" )
	return avg_achieved_gain, probes_decrease, gains_increase



def run_experiment_snapshot(prober, num_target_hops):
	'''
		Run experiment based on snapshot.
	'''
	def probe_target_hops(prober, target_hops, naive):
		prober.reset_all_hops()
		initial_uncertainty = prober.uncertainty_for_hops(target_hops)
		num_probes = prober.probe_hops(target_hops, naive)
		final_uncertainty = prober.uncertainty_for_hops(target_hops)
		inf_gain = 1 - final_uncertainty / initial_uncertainty
		print("Method:", "naive  " if naive else "optimal", 
			"achieved gain", round(inf_gain,2), "after", num_probes, "probes")
		return inf_gain, num_probes
	target_hops = random.sample(prober.lnhopgraph.edges(), num_target_hops)
	inf_gain_optimal, num_probes_optimal 	= probe_target_hops(prober, target_hops, naive=False)
	inf_gain_naive, num_probes_naive 		= probe_target_hops(prober, target_hops, naive=True)
	probes_decrease = 1 - num_probes_optimal / num_probes_naive
	gains_increase = inf_gain_optimal / inf_gain_naive - 1
	print("Number of probes decreased by	", round(100*(probes_decrease),2), "%")
	print("Information gain increased by	", round(100*(gains_increase),2), "%")
	return inf_gain_optimal, probes_decrease, gains_increase


def main():

	parser = argparse.ArgumentParser(description='List the content of a folder')
	parser.add_argument('--num_hops', default=100, type=int)
	parser.add_argument('--use_snapshot', dest='use_snapshot', default=False, action='store_true')
	args = parser.parse_args()

	CAPACITY = 2**20
	NUM_CHANNELS_VALUES = [1,2,3]
	PROBABILITIES = [p / 100.0 for p in range(25, 101, 25)]

	if args.use_snapshot:
		FILENAME = "./snapshot-2020-12-28-balances-uniform.json"
		ENTRY_CHANNEL_CAPACITY = 10*100*1000*1000
		# top 10 nodes by degree as per https://1ml.com/node?order=channelcount
		ENTRY_NODES = [
		"02ad6fb8d693dc1e4569bcedefadf5f72a931ae027dc0f0c544b34c1c6f3b9a02b",
		"03864ef025fde8fb587d989186ce6a4a186895ee44a926bfc370e2c366597a3f8f",
		"0217890e3aad8d35bc054f43acc00084b25229ecff0ab68debd82883ad65ee8266",
		"0331f80652fb840239df8dc99205792bba2e559a05469915804c08420230e23c7c",
		"0242a4ae0c5bef18048fbecf995094b74bfb0f7391418d71ed394784373f41e4f3",
		"03bb88ccc444534da7b5b64b4f7b15e1eccb18e102db0e400d4b9cfe93763aa26d",
		"03abf6f44c355dec0d5aa155bdbdd6e0c8fefe318eff402de65c6eb2e1be55dc3e",
		"02004c625d622245606a1ea2c1c69cfb4516b703b47945a3647713c05fe4aaeb1c",
		"0395033b252c6f40e3756984162d68174e2bd8060a129c0d3462a9370471c6d28f",
		"0390b5d4492dc2f5318e5233ab2cebf6d48914881a33ef6a9c6bcdbb433ad986d0"
		]
		prober = Prober(FILENAME, "PROBER", ENTRY_NODES, ENTRY_CHANNEL_CAPACITY)

	probes_decreases = [[0] * len(PROBABILITIES)] * len(NUM_CHANNELS_VALUES)
	gains_increases = [[0] * len(PROBABILITIES)] * len(NUM_CHANNELS_VALUES)
	achieved_gains = [[0] * len(PROBABILITIES)] * len(NUM_CHANNELS_VALUES)

	for i,num_channels in enumerate(NUM_CHANNELS_VALUES):
		print("\n\nN = ", num_channels)
		for j,probability_enabled in enumerate(PROBABILITIES):
			print("  probability_enabled = ", probability_enabled)
			achieved_gain, probes_decrease, gains_increase = (
				run_experiment_snapshot(prober, args.num_hops) if args.use_snapshot else \
				run_experiment_synthetic(args.num_hops, CAPACITY, num_channels, probability_enabled) )
			achieved_gains[i][j] = achieved_gain
			probes_decreases[i][j] = probes_decrease
			gains_increases[i][j] = gains_increase
	
	# use this for charts
	print("\n== Results ==")
	print("achieved_gains:\n", achieved_gains)
	print("probes_decreases:\n", probes_decreases)
	print("gains_increases:\n", gains_increases)
			

if __name__ == "__main__":
	main()
