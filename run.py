#! /usr/bin/python3

# Copyright (c) University of Luxembourg 2020-2021.
# Developed by Sergei Tikhomirov (sergey.s.tikhomirov@gmail.com), SnT Cryptolux group.

'''
	Run a probing experiment.
'''

from prober import Prober
from hop import Hop
from plot import plot

import random
import argparse
import statistics
import time


def generate_hop(min_N, max_N, min_capacity, max_capacity, probability_bidirectional, balances=None):
	'''
		Generate a random hop.

		Parameters:
		- min_N: minimum number of channels
		- max_N: maximum number of channels
		- min_capacity: minimum capacity of one channel
		- max_capacity: maximum capacity of one channel
		- probability_bidirectional: probability that a channel is enabled in both directions
		- balances: channel balances (generated randomly if None)

		Return:
		- a Hop instance
	'''
	N = random.randint(min_N, max_N)
	capacities = [random.randint(min_capacity, max_capacity) for _ in range(N)]
	# avoid generating hops disabled in both directions (we can't probe them anyway)
	hop_enabled_in_one_direction = False
	while not hop_enabled_in_one_direction:
		enabled_dir0 = []
		enabled_dir1 = []
		for i in range(N):
			is_bidirectional = random.random() < probability_bidirectional
			if is_bidirectional:
				enabled_dir0.append(i)
				enabled_dir1.append(i)
			else:
				if random.random() < probability_bidirectional:
					enabled_dir0.append(i)
				else:
					enabled_dir0.append(i)
		hop_enabled_in_one_direction = enabled_dir0 or enabled_dir0
	#print("Generating hop: capacities", capacities, "enabled_dir0", enabled_dir0, "enabled_dir1", enabled_dir1)
	return Hop(capacities, enabled_dir0, enabled_dir1, balances)


def generate_hops(num_target_hops, N, min_capacity, max_capacity, probability_bidirectional=1, all_max=True):
	'''
		Generate num_target_hops random hops.

		Parameters:
		- num_target_hops: the number of hops to generate
		- max_N: maximum number of channel per hop
		- max_capacity: maximum capacity per channel
		- probability_bidirectional: probability that a channel is enabled in a given direction
		- all_max: if True, minimal N and capacity = max values; if False, both equal 1

		Return:
		- a list of generated hops
	'''
	return [generate_hop(N, N, min_capacity, max_capacity, probability_bidirectional) for _ in range(num_target_hops)]


def probe_single_hop(hop, naive, target_uncertainty_share=0):
	'''
		Do a series of probes until the hop is fully probed.
	'''
	initial_uncertainty = hop.uncertainty
	assert(initial_uncertainty > 0), str(initial_uncertainty) + "\n" + str(hop)
	num_probes = 0
	while (hop.h_u - hop.h_l > 1 and hop.g_u - hop.g_l > 1):
		chosen_dir0 = hop.next_dir()
		if chosen_dir0 is None:
			#print("Hop is disabled in both directions, cannot probe")
			break
		amount = hop.next_a(is_dir0 = chosen_dir0, naive=naive)
		hop.probe(is_dir0=chosen_dir0, amount=amount)
		num_probes += 1
		current_uncertainty = hop.uncertainty
		current_uncertainty_share = current_uncertainty / initial_uncertainty
		if current_uncertainty_share  < target_uncertainty_share:
			#print("\n----------\nTarget reached: current uncertainty share = ", current_uncertainty_share)
			break
	final_uncertainty = hop.uncertainty
	gain = initial_uncertainty - final_uncertainty
	# return gain in bits and used number of probes
	return gain, num_probes


def probe_synthetic_hops(hops, naive):
	'''
		Probe each hop from a list of hops.
	'''
	for hop in hops:
		hop.reset()
	initial_uncertainty_total = sum([hop.uncertainty for hop in hops])
	gains, probes_list = [], []
	for hop in hops:
		gain, probes = probe_single_hop(hop, naive=naive)
		gains.append(gain)
		probes_list.append(probes)
	#print("\nProbed with method:", "naive" if naive else "optimal")
	#print("Total gain:		", round(sum(gains),2), "after", sum(probes_list), "probes")
	#print("Average per hop:	", round(sum(gains)/len(gains),2), "after", sum(probes_list)/len(probes), "probes")
	final_uncertainty_total = sum([hop.uncertainty for hop in hops])
	total_gain_bits = initial_uncertainty_total - final_uncertainty_total
	probing_speed = total_gain_bits / sum(probes_list)
	total_gain = total_gain_bits / initial_uncertainty_total
	return total_gain, probing_speed




def print_data_with_mean_and_variance(data):
	print(data)
	print("  mean:		", 	statistics.mean(data))
	print("  stdev:	", 		statistics.stdev(data))
	print("  variance:	",	statistics.variance(data))


def generate_prober():
	FILENAME = "./snapshot/listchannels-2021-05-23.json"
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
	return prober


def choose_target_hops_with_n_channels(lnhopgraph, max_num_target_hops, num_channels):
	# we only choose targets that are enabled in at least one directions
	potential_target_hops = [(u,v) for u,v,e in lnhopgraph.edges(data=True) if (
		e["hop"].N == num_channels and (e["hop"].can_forward_dir0 or e["hop"].can_forward_dir1))]
	random.shuffle(potential_target_hops)
	return potential_target_hops[:max_num_target_hops]


def probe_snapshot_hops(prober, target_hops, naive):
	prober.reset_all_hops()
	initial_uncertainty_total = prober.uncertainty_for_hops(target_hops)
	num_probes = prober.probe_hops(target_hops, naive)
	final_uncertainty_total = prober.uncertainty_for_hops(target_hops)
	total_gain_bits = initial_uncertainty_total - final_uncertainty_total
	probing_speed = total_gain_bits / num_probes
	total_gain = total_gain_bits / initial_uncertainty_total
	return total_gain, probing_speed


def experiment_1(num_target_hops, num_runs_per_experiment, max_num_channels, use_snapshot):
	'''
		Measure information gain and probing speed on synthetic hops
		consisting of bi-directional channels.
	'''
	BITCOIN = 100*1000*1000
	MIN_CAPACITY_OF_SYNTHETIC_HOPS = 0.01 	* BITCOIN
	MAX_CAPACITY_OF_SYNTHETIC_HOPS = 10 	* BITCOIN
	#NUM_CHANNELS_IN_TARGET_HOPS = [n for n in range(1, max_num_channels + 1)]
	NUM_CHANNELS_IN_TARGET_HOPS = [n for n in range(max_num_channels, max_num_channels + 1)]

	gains_naive_synthetic 		= [0 for _ in range(len(NUM_CHANNELS_IN_TARGET_HOPS))]
	gains_optimal_synthetic 	= [0 for _ in range(len(NUM_CHANNELS_IN_TARGET_HOPS))]
	speed_naive_synthetic 		= [0 for _ in range(len(NUM_CHANNELS_IN_TARGET_HOPS))]
	speed_optimal_synthetic 	= [0 for _ in range(len(NUM_CHANNELS_IN_TARGET_HOPS))]

	gains_naive_snapshot 		= [0 for _ in range(len(NUM_CHANNELS_IN_TARGET_HOPS))]
	gains_optimal_snapshot 		= [0 for _ in range(len(NUM_CHANNELS_IN_TARGET_HOPS))]
	speed_naive_snapshot		= [0 for _ in range(len(NUM_CHANNELS_IN_TARGET_HOPS))]
	speed_optimal_snapshot 		= [0 for _ in range(len(NUM_CHANNELS_IN_TARGET_HOPS))]
	
	if use_snapshot:
		prober = generate_prober()

	# There is only 7 hops with 6 channels, 4 hops with 7 channels
	# It only makes sense to test snapshot-based hops for N from 1 to 5!
	# For larger N, test on synthetic hops

	for i,num_channels in enumerate(NUM_CHANNELS_IN_TARGET_HOPS):
		print("\n\nN = ", num_channels)
		gain_list_naive_synthetic, gain_list_optimal_synthetic = [], []
		speed_list_naive_synthetic, speed_list_optimal_synthetic = [], []
		gain_list_naive_snapshot, gain_list_optimal_snapshot = [], []
		speed_list_naive_snapshot, speed_list_optimal_snapshot = [], []
		for num_experiment in range(num_runs_per_experiment):
			print("  experiment", num_experiment)
			if use_snapshot:
				# pick target hops from snapshot, probe them in isolated mode and via snapshot
				target_hops_nodes = choose_target_hops_with_n_channels(prober.lnhopgraph, 
					max_num_target_hops=num_target_hops, num_channels=num_channels)
				target_hops = [prober.lnhopgraph[u][v]["hop"] for (u,v) in target_hops_nodes]
			else:
				# generate target hops, probe them in isolated mode
				target_hops = generate_hops(num_target_hops, num_channels, 
					MIN_CAPACITY_OF_SYNTHETIC_HOPS, MAX_CAPACITY_OF_SYNTHETIC_HOPS)
			print("Selected" if use_snapshot else "Generated", len(target_hops), "target hops with", num_channels, "channels.")
			gain_naive_synthetic_value,	speed_naive_synthetic_value 		\
			= probe_synthetic_hops(target_hops, naive=True)
			gain_optimal_synthetic_value,	speed_optimal_synthetic_value 	\
			= probe_synthetic_hops(target_hops, naive=False)
			diff_gains = abs((gain_naive_synthetic_value-gain_optimal_synthetic_value) / gain_optimal_synthetic_value)
			max_diff_gains = 0.01
			if(diff_gains > max_diff_gains):
				print("  (!) Relative difference between gains: ", diff_gains)
			gain_list_naive_synthetic.append(			gain_optimal_synthetic_value)
			gain_list_optimal_synthetic.append(			gain_optimal_synthetic_value)
			speed_list_naive_synthetic.append(	speed_naive_synthetic_value)
			speed_list_optimal_synthetic.append(speed_optimal_synthetic_value)
			if use_snapshot:
				gain_optimal_naive_snapshot_value,	speed_naive_snapshot_value = \
				probe_snapshot_hops(prober, target_hops_nodes, naive=True)
				gain_optimal_optimal_snapshot_value,speed_optimal_snapshot_value = \
				probe_snapshot_hops(prober, target_hops_nodes, naive=False)
				#assert(abs((gain_optimal_naive_snapshot_value-gain_optimal_optimal_snapshot_value) / gain_optimal_optimal_snapshot_value) < 0.01)
				gain_list_naive_snapshot.append(			gain_optimal_naive_snapshot_value)
				gain_list_optimal_snapshot.append(			gain_optimal_optimal_snapshot_value)
				speed_list_naive_snapshot.append(	speed_naive_snapshot_value)
				speed_list_optimal_snapshot.append(	speed_optimal_snapshot_value)
		gains_naive_synthetic[i] 	= gain_list_naive_synthetic
		gains_optimal_synthetic[i] 	= gain_list_optimal_synthetic
		speed_naive_synthetic[i]	= speed_list_naive_synthetic
		speed_optimal_synthetic[i]	= speed_list_optimal_synthetic
		if use_snapshot:
			gains_naive_snapshot[i] 	= gain_list_naive_snapshot
			gains_optimal_snapshot[i] 	= gain_list_optimal_snapshot
			speed_naive_snapshot[i]		= speed_list_naive_snapshot
			speed_optimal_snapshot[i]	= speed_list_optimal_snapshot
	y_data_gains_plot = [
		(gains_optimal_synthetic,	"Isolated probing (optimal = naive)",	"--",	"blue"),
		(gains_optimal_snapshot,	"Snapshot probing, optimal",			"-",	"green"),
		(gains_naive_snapshot,		"Snapshot probing, naive",				"-",	"red"), 
		] if use_snapshot else [
		(gains_optimal_synthetic,	"Isolated probing (optimal = naive)",	"--",	"blue")
		]
	y_data_speed_plot = [
		(speed_optimal_synthetic,	"Isolated probing, optimal",	"--",	"green"),
		(speed_naive_synthetic,		"Isolated probing, naive", 		"--",	"red"),
		(speed_optimal_snapshot,	"Snapshot probing, optimal",	"-",	"green"),
		(speed_naive_snapshot,		"Snapshot probing, naive",		"-",	"red"),
		] if use_snapshot else [
		(speed_optimal_synthetic,	"Isolated probing, optimal",	"--",	"green"),
		(speed_naive_synthetic,		"Isolated probing, naive", 		"--",	"red"),
		]
	comment = "Runs per experiment: " + str(num_runs_per_experiment) + ", target hops: " + str(num_target_hops)
	targets_source = "snapshot" if use_snapshot else "synthetic"
	plot(
		x_data 		= NUM_CHANNELS_IN_TARGET_HOPS,
		y_data_list = y_data_gains_plot,
		x_label 	= "Number of channels in target hops. " + comment,
		y_label 	= "Achieved information gain\n (share of initial uncertainty)",
		title		= "Achieved information gain (" + targets_source + " targets)\n",
		filename 	= "channels_gains_" + targets_source)
	plot(
		x_data 		= NUM_CHANNELS_IN_TARGET_HOPS,
		y_data_list = y_data_speed_plot, 
		x_label 	= "Number of channels in target hops. " + comment,
		y_label 	= "Probing speed (bits / probe)", 
		title 		= "Probing speed (" + targets_source + " targets)\n",
		filename 	= "channels_speed_" + targets_source)


def experiment_2(num_target_hops, num_runs_per_experiment):
	'''
		Measure the gain and speed for 3 different configurations of a 2-channel hop.
	'''
	CAPACITY_BIG = 2**20
	CAPACITY_SMALL = 2**15
	BIG_BIG 	= [CAPACITY_BIG, CAPACITY_BIG]
	BIG_SMALL 	= [CAPACITY_BIG, CAPACITY_SMALL]
	SMALL_BIG	= [CAPACITY_SMALL, CAPACITY_BIG]

	ENABLED_BOTH 	= [0,1]
	ENABLED_FIRST 	= [0]
	ENABLED_SECOND 	= [1]
	ENABLED_NONE 	= []

	def get_hop_2_2():
		return Hop(BIG_BIG, ENABLED_BOTH, ENABLED_BOTH)

	def get_hop_2_2_big_small():
		return Hop(BIG_SMALL, ENABLED_BOTH, ENABLED_BOTH)

	def get_hop_2_2_small_big():
		return Hop(SMALL_BIG, ENABLED_BOTH, ENABLED_BOTH)

	def get_hop_1_1():
		return Hop(BIG_BIG, ENABLED_FIRST, ENABLED_SECOND)

	def get_hop_1_1_big_small():
		return Hop(BIG_SMALL, ENABLED_FIRST, ENABLED_SECOND)

	def get_hop_1_1_small_big():
		return Hop(SMALL_BIG, ENABLED_FIRST, ENABLED_SECOND)

	def get_hop_2_1():
		return Hop(BIG_BIG, ENABLED_BOTH, ENABLED_FIRST)

	def get_hop_2_1_big_small():
		return Hop(BIG_SMALL, ENABLED_BOTH, ENABLED_FIRST)

	def get_hop_2_1_small_big():
		return Hop(SMALL_BIG, ENABLED_BOTH, ENABLED_FIRST)

	def get_hop_2_0():
		return Hop(BIG_BIG, ENABLED_BOTH, ENABLED_NONE)

	def get_hop_2_0_big_small():
		return Hop(BIG_SMALL, ENABLED_BOTH, ENABLED_NONE)

	def get_hop_2_0_small_big():
		return Hop(SMALL_BIG, ENABLED_BOTH, ENABLED_NONE)

	def compare_methods(target_hops):
		gain_naive, 	speed_naive 	= probe_synthetic_hops(target_hops, naive=True)
		gain_optimal, 	speed_optimal 	= probe_synthetic_hops(target_hops, naive=False)
		assert(abs((gain_naive-gain_optimal) / gain_optimal) < 0.05), (gain_naive, gain_optimal)
		return gain_optimal, speed_naive, speed_optimal

	all_types = [
	"2_2", "2_2_big_small", "2_2_small_big",
	 "1_1", "1_1_big_small", "1_1_small_big",
	 "2_1", "2_1_big_small", "2_1_small_big", 
	 "2_0", "2_0_big_small", "2_0_small_big"]

	def compare_methods_average(hop_type):
		print("\nHops of type", hop_type)
		if hop_type 	== "2_2":
			get_hop 	= get_hop_2_2
		elif hop_type 	== "2_2_big_small":
			get_hop 	= get_hop_2_2_big_small
		elif hop_type 	== "2_2_small_big":
			get_hop 	= get_hop_2_2_small_big
		elif hop_type 	== "1_1":
			get_hop 	= get_hop_1_1
		elif hop_type 	== "1_1_big_small":
			get_hop 	= get_hop_1_1_big_small
		elif hop_type 	== "1_1_small_big":
			get_hop 	= get_hop_1_1_small_big
		elif hop_type 	== "2_1":
			get_hop 	= get_hop_2_1
		elif hop_type 	== "2_1_big_small":
			print("Big channel enabled in both directions, small channel enabled in one direction")
			get_hop 	= get_hop_2_1_big_small
		elif hop_type 	== "2_1_small_big":
			print("Small channel enabled in both directions, big channel enabled in one direction")
			get_hop 	= get_hop_2_1_small_big
		elif hop_type 	== "2_0":
			get_hop 	= get_hop_2_0
		elif hop_type 	== "2_0_big_small":
			print("Big channel enabled in both directions, small channel enabled in one direction")
			get_hop 	= get_hop_2_0_big_small
		elif hop_type 	== "2_0_small_big":
			print("Small channel enabled in both directions, big channel enabled in one direction")
			get_hop 	= get_hop_2_0_small_big
		else:
			print("Incorrect hop type:", hop_type)
			return
		gain_list, speed_naive_list, speed_optimal_list = [], [], []
		for _ in range(num_runs_per_experiment):
			gain_optimal, speed_naive, speed_optimal = compare_methods([get_hop() for _ in range(num_target_hops)])
			gain_list.append(gain_optimal)
			speed_naive_list.append(speed_naive)
			speed_optimal_list.append(speed_optimal)
		print("Gains (mean):		", 	round(statistics.mean(gain_list),2))
		#print("  stdev:", statistics.stdev(gain_list))
		speed_naive_mean = statistics.mean(speed_naive_list)
		speed_optimal_mean = statistics.mean(speed_optimal_list)
		print("Speed naive (mean):	", round(speed_naive_mean,2))
		#print("  stdev:", statistics.stdev(speed_naive_list))
		print("Speed optimal (mean):	", round(speed_optimal_mean,2))
		#print("  stdev:", statistics.stdev(speed_optimal_list))
		print("Advantage:		", round((speed_optimal_mean-speed_naive_mean)/speed_naive_mean,2))

	for hop_type in all_types:
		compare_methods_average(hop_type)


def experiment_3(num_target_hops, num_runs_per_experiment, max_ratio):
	'''
		Study two-channel hops depending on ratio of long side to short.
	'''

	SHORT_SIDE_CAPACITY = 2**20
	RATIOS = [r for r in range(1, max_ratio + 1)]

	achieved_gains_ratios 	= [0 for _ in range(len(RATIOS))]
	speed_naive_ratios 		= [0 for _ in range(len(RATIOS))]
	speed_optimal_ratios 	= [0 for _ in range(len(RATIOS))]

	for i,ratio in enumerate(RATIOS):
		print("\n\nR = ", ratio)
		capacities = [SHORT_SIDE_CAPACITY, ratio * SHORT_SIDE_CAPACITY]
		gain_list, speed_list_naive, speed_list_optimal = [], [], []
		for _ in range(num_runs_per_experiment):
			target_hops = [Hop(capacities, [0,1], [0,1]) for _ in range(num_target_hops)]
			gain_naive,		speed_naive 	= probe_synthetic_hops(target_hops, naive=True)
			gain_optimal,	speed_optimal 	= probe_synthetic_hops(target_hops, naive=False)
			assert(abs((gain_naive-gain_optimal) / gain_optimal) < 0.05), (gain_naive, gain_optimal)
			gain_list.append(gain_optimal)
			speed_list_naive.append(speed_naive)
			speed_list_optimal.append(speed_optimal)
		achieved_gains_ratios[i] = gain_list
		speed_naive_ratios[i]	= speed_list_naive
		speed_optimal_ratios[i]	= speed_list_optimal


	comment = "Runs per experiment: " + str(num_runs_per_experiment) + ", target hops: " + str(num_target_hops)
	plot(
		x_data		= RATIOS,
		y_data_list = [(achieved_gains_ratios,"")], 
		x_label 	= "Ratio of capacities\n" + comment,
		y_label 	= "Achieved information gain",
		title		= "Achieved information gain (synthetic hops)",
		filename 	= "ratios_gains")
	plot(
		x_data		= RATIOS,
		y_data_list = [(speed_naive_ratios,"Naive method"),(speed_optimal_ratios, "Optimal method")], 
		x_label 	= "Ratio of capacities\n" + comment,
		y_label 	= "Probing speed (bits / probe)", 
		title 		= "Probing speed with naive and optimal methods (synthetic hops)",
		filename 	= "ratios_speed")



def main():

	parser = argparse.ArgumentParser()
	parser.add_argument('--num_target_hops', default=100, type=int)
	parser.add_argument('--num_runs_per_experiment', default=10, type=int)
	parser.add_argument('--max_num_channels', default=10, type=int)
	parser.add_argument('--use_snapshot', dest='use_snapshot', action='store_true')
	args = parser.parse_args()

	if args.use_snapshot and args.max_num_channels > 5:
		print("Too high max_num_channels: snapshot doesn't have that many hops with that many channels.")
		exit()
	
	experiment_1(args.num_target_hops, args.num_runs_per_experiment, args.max_num_channels, args.use_snapshot)
	#experiment_2(args.num_target_hops, args.num_runs_per_experiment)
	#experiment_3(args.num_target_hops, args.num_runs_per_experiment, max_ratio=10)

	


if __name__ == "__main__":
	start_time = time.time()
	main()
	end_time = time.time()
	print("Completed in", round(end_time - start_time), "seconds.")
