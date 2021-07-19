#! /usr/bin/python3

# Copyright (c) University of Luxembourg 2020-2021.
# Developed by Sergei Tikhomirov (sergey.s.tikhomirov@gmail.com), SnT Cryptolux group.


import random

from hop import Hop


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


def probe_single_hop(hop, naive, jamming):
	'''
		Do a series of probes until the hop is fully probed.
	'''
	initial_uncertainty = hop.uncertainty
	#assert(initial_uncertainty > 0), "Uncertainty = " + str(initial_uncertainty) + "\n" + str(hop)
	# probe without jamming until possible
	#print("\nProbing without jamming")
	num_probes, num_jams = probe_hop_without_jamming(hop, naive), 0
	if jamming:
		for i in range(hop.N):
			#print("\nJamming-enhanced probing channel", i)
			hop.unjam(i, direction=True)
			hop.unjam(i, direction=False)
			# TODO: can we jam in one direction only? (fewer jams)
			num_jams += hop.jam_all_except_in_direction(i, direction=True)
			num_jams += hop.jam_all_except_in_direction(i, direction=False)
			num_probes_i, num_jams_i = jam_hop_and_probe_single_channel(hop, naive, i)
			num_probes += num_probes_i
			num_jams += num_jams_i
	hop.unjam_all()
	final_uncertainty = hop.uncertainty
	gain = initial_uncertainty - final_uncertainty
	# return gain in bits and used number of probes
	return gain, num_probes, num_jams

def probe_hop_without_jamming(hop, naive):
	num_probes = 0
	while hop.worth_probing_h() or hop.worth_probing_g():
		chosen_dir0 = hop.next_dir(naive, jamming=False)
		if chosen_dir0 is None:
			print("Hop is disabled in both directions, cannot probe")
			break
		amount = hop.next_a(chosen_dir0, naive, jamming=False)
		hop.probe(chosen_dir0, amount)
		num_probes += 1
	return num_probes

def jam_hop_and_probe_single_channel(hop, naive, i):
	num_probes, num_jams = 0, 0
	while hop.worth_probing_channel(i):
		chosen_dir0 = hop.next_dir(naive, jamming=True)
		if chosen_dir0 is None:
			print("Hop is disabled in both directions, cannot probe")
			break
		amount = hop.next_a(chosen_dir0, naive, jamming=True)
		hop.probe(chosen_dir0, amount)
		num_probes += 1
	return num_probes, num_jams


def probe_hops_isolated(hops, naive, jamming=False):
	'''
		Probe each hop from a list of hops.
	'''
	for hop in hops:
		hop.reset_estimates()
	initial_uncertainty_total = sum([hop.uncertainty for hop in hops])
	gains, probes_list = [], []
	for hop in hops:
		gain, probes, jams = probe_single_hop(hop, naive=naive, jamming=jamming)
		gains.append(gain)
		# count jams as probes (they are payments too!)
		probes_list.append(probes + jams)
	#print("\nProbed with method:", "naive" if naive else "optimal", "with jamming" if jamming else "without jamming")
	#print("Total gain:		", round(sum(gains),2), "after", sum(probes_list), "probes")
	#print("Average per hop:	", round(sum(gains)/len(gains),2), "after", sum(probes_list)/len(probes_list), "probes")
	final_uncertainty_total = sum([hop.uncertainty for hop in hops])
	#print("Final uncertainty:", final_uncertainty_total)
	total_gain_bits = initial_uncertainty_total - final_uncertainty_total
	probing_speed = total_gain_bits / sum(probes_list)
	total_gain = total_gain_bits / initial_uncertainty_total
	return total_gain, probing_speed
