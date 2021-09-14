#! /usr/bin/python3

# Copyright (c) University of Luxembourg 2020-2021.
# Developed by Sergei Tikhomirov (sergey.s.tikhomirov@gmail.com), SnT Cryptolux group.

'''
	Run experiments as described in the paper.
'''

import statistics

from synthetic import generate_hops, probe_hops_direct
from hop import Hop
from plot import plot


def experiment_1(prober, num_target_hops, num_runs_per_experiment, 
	min_num_channels, max_num_channels, use_snapshot, jamming):
	'''
		Measure the information gain and probing speed for direct and remote probing.

		Generate or choose target hops with various number of channels.
		Probe the target hops in direct and remote mode (if prober is provided), using BS and NBS amount choice methods.
		Measure and plot the final achieved information gain and probing speed.

		Parameters:
		- prober: the Prober object (None to run only direct probing on synthetic hops)
		- num_target_hops: how many target hops to choose / generate
		- num_runs_per_experiments: how many experiments to run (gain and speed are averaged)
		- min_num_channels: the minimal number of channels in hops to consider
		- max_num_channels: the maximal number of channels in hops to consider
		- use_snapshot:
			if False, run only direct probing on synthetic hops; 
			if True, run direct and remote probing on synthetic and snapshot hops.
		- jamming: use jamming (after h and g are fully probed without jamming)

		Return: None (saves the resulting plots)
	'''

	print("\n\n**** Running experiment 1 ****")
	assert(not use_snapshot or prober is not None)

	BITCOIN = 100*1000*1000
	MIN_CAPACITY_SYNTHETIC = 0.01 	* BITCOIN
	MAX_CAPACITY_SYNTHETIC = 10 	* BITCOIN
	NUM_CHANNELS_IN_TARGET_HOPS = [n for n in range(min_num_channels, max_num_channels + 1)]
	# Hops with 5+ channels are very rare in the snapshot.

	gains_bs_synthetic 		= [0 for _ in range(len(NUM_CHANNELS_IN_TARGET_HOPS))]
	gains_nbs_synthetic 	= [0 for _ in range(len(NUM_CHANNELS_IN_TARGET_HOPS))]
	speed_bs_synthetic 		= [0 for _ in range(len(NUM_CHANNELS_IN_TARGET_HOPS))]
	speed_nbs_synthetic 	= [0 for _ in range(len(NUM_CHANNELS_IN_TARGET_HOPS))]
	gains_bs_snapshot 		= [0 for _ in range(len(NUM_CHANNELS_IN_TARGET_HOPS))]
	gains_nbs_snapshot 		= [0 for _ in range(len(NUM_CHANNELS_IN_TARGET_HOPS))]
	speed_bs_snapshot		= [0 for _ in range(len(NUM_CHANNELS_IN_TARGET_HOPS))]
	speed_nbs_snapshot 		= [0 for _ in range(len(NUM_CHANNELS_IN_TARGET_HOPS))]

	for i, num_channels in enumerate(NUM_CHANNELS_IN_TARGET_HOPS):
		print("\n\nN = ", num_channels)
		gain_list_bs_synthetic, gain_list_nbs_synthetic = [], []
		speed_list_bs_synthetic, speed_list_nbs_synthetic = [], []
		gain_list_bs_snapshot, gain_list_nbs_snapshot = [], []
		speed_list_bs_snapshot, speed_list_nbs_snapshot = [], []
		for num_experiment in range(num_runs_per_experiment):
			print("  experiment", num_experiment)
			if use_snapshot:
				# pick target hops from snapshot, probe them in direct and remote modes
				target_hops_node_pairs = prober.choose_target_hops_with_n_channels(num_target_hops, num_channels)
				target_hops = [prober.lnhopgraph[u][v]["hop"] for (u,v) in target_hops_node_pairs]
			else:
				# generate target hops, probe them in direct mode
				target_hops = generate_hops(num_target_hops, num_channels, MIN_CAPACITY_SYNTHETIC, MAX_CAPACITY_SYNTHETIC)
			print("Selected" if use_snapshot else "Generated", len(target_hops), "target hops with", num_channels, "channels.")
			# probe target hops in direct mode
			gain_bs_synthetic_value, speed_bs_synthetic_value = probe_hops_direct(target_hops, bs=True, jamming=jamming)
			gain_nbs_synthetic_value, speed_nbs_synthetic_value = probe_hops_direct(target_hops, bs=False, jamming=jamming)
			gain_list_bs_synthetic.append(gain_nbs_synthetic_value)
			gain_list_nbs_synthetic.append(gain_nbs_synthetic_value)
			speed_list_bs_synthetic.append(speed_bs_synthetic_value)
			speed_list_nbs_synthetic.append(speed_nbs_synthetic_value)
			if use_snapshot:
				# probe target hops in snapshot mode
				gain_nbs_bs_snapshot_value,	speed_bs_snapshot_value = prober.probe_hops(target_hops_node_pairs, bs=True, jamming=jamming)
				gain_nbs_snapshot_value,speed_nbs_snapshot_value = prober.probe_hops(target_hops_node_pairs, bs=False, jamming=jamming)
				gain_list_bs_snapshot.append(gain_nbs_bs_snapshot_value)
				gain_list_nbs_snapshot.append(gain_nbs_snapshot_value)
				speed_list_bs_snapshot.append(speed_bs_snapshot_value)
				speed_list_nbs_snapshot.append(speed_nbs_snapshot_value)
		gains_bs_synthetic[i] 	= gain_list_bs_synthetic
		gains_nbs_synthetic[i] 	= gain_list_nbs_synthetic
		speed_bs_synthetic[i]	= speed_list_bs_synthetic
		speed_nbs_synthetic[i]	= speed_list_nbs_synthetic
		if use_snapshot:
			gains_bs_snapshot[i] 	= gain_list_bs_snapshot
			gains_nbs_snapshot[i] 	= gain_list_nbs_snapshot
			speed_bs_snapshot[i]	= speed_list_bs_snapshot
			speed_nbs_snapshot[i]	= speed_list_nbs_snapshot
	# prepare data for information gains plot
	y_data_gains_plot = [
		(gains_nbs_synthetic,	"Direct probing (NBS = BS)","--",	"blue"),
		(gains_nbs_snapshot,	"Remote probing, NBS",		"-",	"green"),
		(gains_bs_snapshot,		"Remote probing, BS",		"-",	"red"), 
		] if use_snapshot else [
		(gains_nbs_synthetic,	"Direct probing (NBS = BS)","--",	"blue")
		]
	# prepare data for probing speeds plot
	y_data_speed_plot = [
		(speed_nbs_synthetic,	"Direct probing, NBS",	"--",	"green"),
		(speed_bs_synthetic,	"Direct probing, BS", 	"--",	"red"),
		(speed_nbs_snapshot,	"Remote probing, NBS",	"-",	"green"),
		(speed_bs_snapshot,		"Remote probing, BS",	"-",	"red"),
		] if use_snapshot else [
		(speed_nbs_synthetic,	"Direct probing, NBS",	"--",	"green"),
		(speed_bs_synthetic,	"Direct probing, BS", 	"--",	"red"),
		]
	comment = ("Runs per experiment: " + str(num_runs_per_experiment) + 
		", target hops: " + str(num_target_hops) + 
		(", snapshot date: " + prober.snapshot_date) if use_snapshot else "")
	targets_source = "snapshot" if use_snapshot else "synthetic"
	jamming_suffix = "jamming-enhanced" if jamming else "non-enhanced"
	extension = ".pdf"
	plot(
		x_data 		= NUM_CHANNELS_IN_TARGET_HOPS,
		y_data_list = y_data_gains_plot,
		x_label 	= "Number of channels in target hops.\n" + comment,
		y_label 	= "Achieved information gain\n (share of initial uncertainty)",
		title		= "Achieved information gain (" + jamming_suffix + " probing)\n",
		filename 	= "channels_gains_" + targets_source + "_" + jamming_suffix,
		extension	= extension)
	plot(
		x_data 		= NUM_CHANNELS_IN_TARGET_HOPS,
		y_data_list = y_data_speed_plot, 
		x_label 	= "Number of channels in target hops.\n" + comment,
		y_label 	= "Probing speed (bits / message)", 
		title 		= "Probing speed (" + jamming_suffix + " probing)\n",
		filename 	= "channels_speed_" + targets_source + "_" + jamming_suffix,
		extension	= extension)

	print("\n\n**** Experiment 1 complete ****")


def experiment_2(num_target_hops, num_runs_per_experiment):
	'''
		Measure the information gain and probing speed for different configurations of a 2-channel hop.

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
		gain_bs, 	speed_bs 	= probe_hops_direct(target_hops, bs = True, jamming = False)
		gain_nbs, 	speed_nbs 	= probe_hops_direct(target_hops, bs = False, jamming = False)
		assert(abs((gain_bs-gain_nbs) / gain_nbs) < 0.05), (gain_bs, gain_nbs)
		return gain_nbs, speed_bs, speed_nbs

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
		gain_list, speed_bs_list, speed_nbs_list = [], [], []
		for _ in range(num_runs_per_experiment):
			gain_nbs, speed_bs, speed_nbs = compare_methods([get_hop() for _ in range(num_target_hops)])
			gain_list.append(gain_nbs)
			speed_bs_list.append(speed_bs)
			speed_nbs_list.append(speed_nbs)
		print("Gains (mean):		", 	round(statistics.mean(gain_list),2))
		#print("  stdev:", statistics.stdev(gain_list))
		speed_bs_mean = statistics.mean(speed_bs_list)
		speed_nbs_mean = statistics.mean(speed_nbs_list)
		print("Speed BS (mean):	", round(speed_bs_mean,2))
		#print("  stdev:", statistics.stdev(speed_bs_list))
		print("Speed NBS (mean):	", round(speed_nbs_mean,2))
		#print("  stdev:", statistics.stdev(speed_nbs_list))
		print("Advantage:		", round((speed_nbs_mean-speed_bs_mean)/speed_bs_mean,2))

	for hop_type in all_types:
		compare_methods_average(hop_type)

	print("\n\n**** Experiment 2 complete ****")


def experiment_3(num_target_hops, num_runs_per_experiment, max_ratio):
	'''
		Study two-channel hops depending on ratio of long side to short.
		(This experiment was excluded from the 2021-09 version of the paper.)

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
	speed_bs_ratios 		= [0 for _ in range(len(RATIOS))]
	speed_nbs_ratios 		= [0 for _ in range(len(RATIOS))]

	for i,ratio in enumerate(RATIOS):
		#print("\n\nR = ", ratio)
		capacities = [SHORT_SIDE_CAPACITY, ratio * SHORT_SIDE_CAPACITY]
		gain_list, speed_list_bs, speed_list_nbs = [], [], []
		for _ in range(num_runs_per_experiment):
			target_hops = [Hop(capacities, [0,1], [0,1]) for _ in range(num_target_hops)]
			gain_bs,	speed_bs 	= probe_hops_direct(target_hops, bs = True, jamming = False)
			gain_nbs,	speed_nbs 	= probe_hops_direct(target_hops, bs = False, jamming = False)
			assert(abs((gain_bs-gain_nbs) / gain_nbs) < 0.05), (gain_bs, gain_nbs)
			gain_list.append(gain_nbs)
			speed_list_bs.append(speed_bs)
			speed_list_nbs.append(speed_nbs)
		achieved_gains_ratios[i] = gain_list
		speed_bs_ratios[i]	= speed_list_bs
		speed_nbs_ratios[i]	= speed_list_nbs

	comment = "Runs per experiment: " + str(num_runs_per_experiment) + ", target hops: " + str(num_target_hops)
	plot(
		x_data		= RATIOS,
		y_data_list = [(achieved_gains_ratios, "Direct probing (bs = nbs)", "-", "blue")], 
		x_label 	= "Ratio of capacities. " + comment,
		y_label 	= "Achieved information gain",
		title		= "Achieved information gain (synthetic hops)",
		filename 	= "ratios_gains")
	plot(
		x_data		= RATIOS,
		y_data_list = [
		(speed_bs_ratios, "Direct probing, bs", "-", "red"),
		(speed_nbs_ratios, "Direct probing, nbs", "-", "green")], 
		x_label 	= "Ratio of capacities. " + comment,
		y_label 	= "Probing speed (bits / message)", 
		title 		= "Probing speed with bs and nbs methods (synthetic hops)",
		filename 	= "ratios_speed")

	print("\n\n**** Experiment 3 complete ****")
