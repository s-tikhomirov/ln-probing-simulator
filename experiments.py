#! /usr/bin/python3

# Copyright (c) University of Luxembourg 2020-2021.
# Developed by Sergei Tikhomirov (sergey.s.tikhomirov@gmail.com), SnT Cryptolux group.

'''
	Run experiments as described in the paper.
'''

import statistics

from isolated import generate_hops, probe_hops_isolated
from hop import Hop
from plot import plot


def experiment_1(prober, num_target_hops, num_runs_per_experiment, max_num_channels, use_snapshot, jamming):
	'''
		Measure the information gain and probing speed for isolated and snapshot-based probing.

		Generate or choose target hops with various number of channels.
		Probe the target hops in isolated and snapshot-based mode (if prober is provided),
		using naive and optimal amount choice method.
		Measure and plot the achieved information gain and probing speed.
		See Section 5.2.1 in the paper.

		Parameters:
		- prober: the Prober object (None to run only isolated probing on synthetic hops)
		- num_target_hops: how many target hops to choose / generate
		- num_runs_per_experiments: how many experiments to run (gain and speed are averaged)
		- max_num_channels: consider target hops containing from 1 to this many channels
		- use_snapshot: if False, run only isolated probing on synthetic hops; 
		if True, run isolated and snapshot-based probing on synthetic and snapshot hops.
		- jamming: use jamming (after h and g are fully probed without jamming)

		Return: None (saves the resulting plots)
	'''

	print("\n\n**** Running experiment 1 ****")

	BITCOIN = 100*1000*1000
	MIN_CAPACITY_OF_SYNTHETIC_HOPS = 0.01 	* BITCOIN
	MAX_CAPACITY_OF_SYNTHETIC_HOPS = 10 	* BITCOIN
	NUM_CHANNELS_IN_TARGET_HOPS = [n for n in range(1, max_num_channels + 1)]

	gains_naive_synthetic 		= [0 for _ in range(len(NUM_CHANNELS_IN_TARGET_HOPS))]
	gains_optimal_synthetic 	= [0 for _ in range(len(NUM_CHANNELS_IN_TARGET_HOPS))]
	speed_naive_synthetic 		= [0 for _ in range(len(NUM_CHANNELS_IN_TARGET_HOPS))]
	speed_optimal_synthetic 	= [0 for _ in range(len(NUM_CHANNELS_IN_TARGET_HOPS))]

	gains_naive_snapshot 		= [0 for _ in range(len(NUM_CHANNELS_IN_TARGET_HOPS))]
	gains_optimal_snapshot 		= [0 for _ in range(len(NUM_CHANNELS_IN_TARGET_HOPS))]
	speed_naive_snapshot		= [0 for _ in range(len(NUM_CHANNELS_IN_TARGET_HOPS))]
	speed_optimal_snapshot 		= [0 for _ in range(len(NUM_CHANNELS_IN_TARGET_HOPS))]
	
	assert(not use_snapshot or prober is not None)

	# There are only 7 hops with 6 channels and 4 hops with 7 channels in the snapshot from 2021-05-23
	# It only makes sense to consider snapshot-based hops for N from 1 to 5!
	# For larger N, we only consider on synthetic hops.

	for i, num_channels in enumerate(NUM_CHANNELS_IN_TARGET_HOPS):
		print("\n\nN = ", num_channels)
		gain_list_naive_synthetic, gain_list_optimal_synthetic = [], []
		speed_list_naive_synthetic, speed_list_optimal_synthetic = [], []
		gain_list_naive_snapshot, gain_list_optimal_snapshot = [], []
		speed_list_naive_snapshot, speed_list_optimal_snapshot = [], []
		for num_experiment in range(num_runs_per_experiment):
			print("  experiment", num_experiment)
			if use_snapshot:
				# pick target hops from snapshot, probe them in isolated mode and via snapshot
				target_hops_nodes = prober.choose_target_hops_with_n_channels(
					max_num_target_hops=num_target_hops, num_channels=num_channels)
				target_hops = [prober.lnhopgraph[u][v]["hop"] for (u,v) in target_hops_nodes]
			else:
				# generate target hops, probe them in isolated mode
				target_hops = generate_hops(num_target_hops, num_channels, 
					MIN_CAPACITY_OF_SYNTHETIC_HOPS, MAX_CAPACITY_OF_SYNTHETIC_HOPS)
			print("Selected" if use_snapshot else "Generated", len(target_hops), "target hops with", num_channels, "channels.")
			# probe target hops in isolated mode
			gain_naive_synthetic_value,	speed_naive_synthetic_value \
			= probe_hops_isolated(target_hops, naive=True, jamming=jamming)
			gain_optimal_synthetic_value, speed_optimal_synthetic_value \
			= probe_hops_isolated(target_hops, naive=False, jamming=jamming)
			diff_gains = abs((gain_naive_synthetic_value-gain_optimal_synthetic_value) / gain_optimal_synthetic_value)
			max_diff_gains = 0.01
			if(diff_gains > max_diff_gains):
				print("  (!) Relative difference between gains: ", diff_gains)
			gain_list_naive_synthetic.append(			gain_optimal_synthetic_value)
			gain_list_optimal_synthetic.append(			gain_optimal_synthetic_value)
			speed_list_naive_synthetic.append(	speed_naive_synthetic_value)
			speed_list_optimal_synthetic.append(speed_optimal_synthetic_value)
			if use_snapshot:
				# probe target hops in snapshot mode
				gain_optimal_naive_snapshot_value,	speed_naive_snapshot_value = \
				prober.probe_hops(target_hops_nodes, naive=True, jamming=jamming)
				gain_optimal_optimal_snapshot_value,speed_optimal_snapshot_value = \
				prober.probe_hops(target_hops_nodes, naive=False, jamming=jamming)
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
	# prepare data for information gains plot
	y_data_gains_plot = [
		(gains_optimal_synthetic,	"Isolated probing (optimal = naive)",	"--",	"blue"),
		(gains_optimal_snapshot,	"Snapshot probing, optimal",			"-",	"green"),
		(gains_naive_snapshot,		"Snapshot probing, naive",				"-",	"red"), 
		] if use_snapshot else [
		(gains_optimal_synthetic,	"Isolated probing (optimal = naive)",	"--",	"blue")
		]
	# prepare data for probing speeds plot
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
	jamming_suffix = "_jamming" if jamming else ""
	plot(
		x_data 		= NUM_CHANNELS_IN_TARGET_HOPS,
		y_data_list = y_data_gains_plot,
		x_label 	= "Number of channels in target hops. " + comment,
		y_label 	= "Achieved information gain\n (share of initial uncertainty)",
		title		= "Achieved information gain (" + targets_source + " targets)\n",
		filename 	= "channels_gains_" + targets_source + jamming_suffix)
	plot(
		x_data 		= NUM_CHANNELS_IN_TARGET_HOPS,
		y_data_list = y_data_speed_plot, 
		x_label 	= "Number of channels in target hops. " + comment,
		y_label 	= "Probing speed (bits / probe)", 
		title 		= "Probing speed (" + targets_source + " targets)\n",
		filename 	= "channels_speed_" + targets_source + jamming_suffix)

	print("\n\n**** Experiment 1 complete ****")


def experiment_2(num_target_hops, num_runs_per_experiment):
	'''
		Measure the information gain and probing speed for 3 different configurations of a 2-channel hop.
		See Section 5.2.2 in the paper.

		Parameters:
		- num_target_hops: how man target hops to consider
		- num_runs_per_experiment: how many times to run each experiment (results are averaged)

		Return: None (print resulting stats)
	'''

	print("\n\n**** Running experiment 2 ****")

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
		gain_naive, 	speed_naive 	= probe_hops_isolated(target_hops, naive = True, jamming = False)
		gain_optimal, 	speed_optimal 	= probe_hops_isolated(target_hops, naive = False, jamming = False)
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

	print("\n\n**** Experiment 2 complete ****")


def experiment_3(num_target_hops, num_runs_per_experiment, max_ratio):
	'''
		Study two-channel hops depending on ratio of long side to short.
		See Section 5.2.3 in the paper.

		Parameters:
		- num_target_hops: how many target hops to consider
		- num_runs_per_experiment: how many times to run each experiment (results are averaged)
		- max_ratio: consider the ratio of channel capacities from 1 to max_ratio

		Return: None (save resulting plots)
	'''

	print("\n\n**** Running experiment 3 ****")

	SHORT_SIDE_CAPACITY = 2**20
	RATIOS = [r for r in range(1, max_ratio + 1)]

	achieved_gains_ratios 	= [0 for _ in range(len(RATIOS))]
	speed_naive_ratios 		= [0 for _ in range(len(RATIOS))]
	speed_optimal_ratios 	= [0 for _ in range(len(RATIOS))]

	for i,ratio in enumerate(RATIOS):
		#print("\n\nR = ", ratio)
		capacities = [SHORT_SIDE_CAPACITY, ratio * SHORT_SIDE_CAPACITY]
		gain_list, speed_list_naive, speed_list_optimal = [], [], []
		for _ in range(num_runs_per_experiment):
			target_hops = [Hop(capacities, [0,1], [0,1]) for _ in range(num_target_hops)]
			gain_naive,		speed_naive 	= probe_hops_isolated(target_hops, naive = True, jamming = False)
			gain_optimal,	speed_optimal 	= probe_hops_isolated(target_hops, naive = False, jamming = False)
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
		y_data_list = [(achieved_gains_ratios, "Isolated probing (naive = optimal)", "-", "blue")], 
		x_label 	= "Ratio of capacities. " + comment,
		y_label 	= "Achieved information gain",
		title		= "Achieved information gain (synthetic hops)",
		filename 	= "ratios_gains")
	plot(
		x_data		= RATIOS,
		y_data_list = [
		(speed_naive_ratios, "Isolated probing, naive", "-", "red"),
		(speed_optimal_ratios, "Isolated probing, optimal", "-", "green")], 
		x_label 	= "Ratio of capacities. " + comment,
		y_label 	= "Probing speed (bits / probe)", 
		title 		= "Probing speed with naive and optimal methods (synthetic hops)",
		filename 	= "ratios_speed")

	print("\n\n**** Experiment 3 complete ****")
