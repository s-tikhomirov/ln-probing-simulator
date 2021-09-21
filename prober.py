#! /usr/bin/python3

# Copyright © University of Luxembourg 2020-2021.
# Developed by Sergei Tikhomirov (sergey.s.tikhomirov@gmail.com), SnT Cryptolux group.

'''
	A model of an attacker who issues probes and updates balance estimates.
'''


from hop import Hop, dir0, dir1
from graph import create_multigraph_from_snapshot, ln_multigraph_to_hop_graph

import networkx as nx
from random import random, shuffle


class Prober:

	def __init__(self, snapshot_filename, node_id, entry_nodes, entry_channel_capacity, granularity=1):
		'''
			Initialize a Prober.

			Parameters:
			- snapshot_filename: a file with a clightning's listchannels.json snapshot
			- node_id: the node ID for the prober
			- entry_nodes: node IDs of nodes that the prober opens channels to
			- entry_channel_capacity: the capacity of each entry channel
			- granularity: the prober wants to know balance up to this granularity (in satoshis)
		'''
		self.our_node_id = node_id
		# parse snapshot date from filename to include in plot title
		self.snapshot_date = snapshot_filename[-len("yyyy-mm-dd.json"):-len(".json")]
		ln_multigraph = create_multigraph_from_snapshot(snapshot_filename)
		self.lnhopgraph = ln_multigraph_to_hop_graph(ln_multigraph)
		for entry_node in entry_nodes:
			self.open_channel(self.our_node_id, entry_node, entry_channel_capacity)
		self.local_routing_graph = self.lnhopgraph.to_directed()


	def __str__(self):
		return "\n".join([str(self.lnhopgraph[first][second]["hop"]) for first, second in self.lnhopgraph.edges()])


	def open_channel(self, first, second, capacity, push_satoshis=0):
		'''
			Add a new channel to the LN model graph.

			Parameters:
			- first: the node opening the channel
			- second: the node accepting the channel
			- capacity: the new channel's capacity
			- push_satoshis: the initial balance of second (default: 0, i.e., all capacity is at first)
		'''
		if first not in self.lnhopgraph.nodes():
			self.lnhopgraph.add_node(first)
		if second not in self.lnhopgraph.nodes():
			self.lnhopgraph.add_node(second)
		direction = dir0 if first < second else dir1
		balance_at_first = capacity if direction == dir0 else 0
		if self.lnhopgraph.has_edge(first, second):
			hop = self.lnhopgraph[first][second]["hop"]
			capacities = hop.c.append(capacity)
			if direction == dir0:
				e_dir0 = hop.e[dir0].append(len(capacities) + 1)
			else:
				e_dir1 = hop.e[dir1].append(len(capacities) + 1)
			balances = hop.balances.append(balance_at_first)
			updated_hop = Hop(capacities, e_dir0, e_dir1, balances)
			#print("Updated hop:", updated_hop)
			self.lnhopgraph[first][second]["hop"] = updated_hop
		else:
			self.lnhopgraph.add_edge(first, second)
			e_dir0, e_dir1 = ([0], []) if direction == dir0 else ([], [0])
			self.lnhopgraph[first][second]["hop"] = Hop([capacity], e_dir0, e_dir1, [balance_at_first])


	def filtered_routing_graph_for_amount(self, amount, exclude_nodes):
		'''
			Create a filtered directed routing graph.

			For each routing attempt, we create a new graph view that excludes 
			  edges that we know cannot forward the required amount.

			Parameters:
			- amount: the required payment amount
			- exclude_nodes: additionally, exclude these nodes from the view
		'''
		def filter_edge(n1, n2):
			'''
				Return True if the edge is kept, False if it is excluded.

				Parameters:
				- n1, n2: node IDs of the vertices
			'''
			hop = self.lnhopgraph[n1][n2]["hop"]
			direction = dir0 if n1 < n2 else dir1
			if direction == dir0:
				return hop.can_forward(dir0) and amount <= hop.h_u
			else:
				return hop.can_forward(dir1) and amount <= hop.g_u
		def filter_node(n):
			'''
				Return True if the node is kept, False if it is excluded.

				A generic User generally shouldn't exclude nodes.
				A Prober, however, excludes the target node and calculates routes to the previous node
				  to ensure the route includes the target hop as the last hop.

				Parameters:
				- n: node ID of the node
			'''
			return True if not exclude_nodes else n not in exclude_nodes
		return nx.subgraph_view(self.local_routing_graph, filter_node=filter_node, filter_edge=filter_edge)


	def paths_for_amount(self, target_hop, amount, exclude_nodes=[], max_paths_suggested=None):
		'''
			Create a generator for paths suitable for the given amount w.r.t. to our knowledge so far.
			Return None is no such path exists.

			Parameters:
			- n1: the first target node ID
			- n2: the second target node ID
			- amount: the amount to send (in satoshis)
			- exclude_nodes: the list of nodes to exclude form paths
			- max_paths_suggested: stop generation after this many paths have been generated

			Return:
			- next_path: the next path, or StopIteration if no more paths exist or max_paths_suggested exceeded
		'''
		(n1, n2) = target_hop
		routing_graph = self.filtered_routing_graph_for_amount(amount, exclude_nodes)
		if n1 not in routing_graph:
			#print("Target", n1, "not in filtered graph, can't find path.")
			yield from ()
		if not nx.has_path(routing_graph, self.our_node_id, n1):
			#print("No path from", self.our_node_id, "to", n1)
			yield from ()
		paths = nx.shortest_simple_paths(routing_graph, source=self.our_node_id, target=n1)
		paths_suggested = 0
		while (max_paths_suggested is None or paths_suggested < max_paths_suggested):
			try:
				next_path = next(paths)
				paths_suggested += 1
				#print("Found path after suggested", paths_suggested, "paths:", next_path)
				yield next_path + [n2]
			except nx.exception.NetworkXNoPath:
				yield from ()
		yield from ()


	def issue_probe_along_path(self, path, amount):
		'''
			Send a probe along a path and observe the result.

			Parameters:
			- path: a list of node pairs defining a path
			- amount: the probe amount

			Return:
			- reached_target: True if the probe reached (either passed or failed) the target hop,
			  False if the probe failed at an intermediary hop
		'''
		# ensure we don't probe our own channels
		assert(path[0] == self.our_node_id)
		node_pairs = [p for p in zip(path, path[1:])]
		reached_target = False
		for n1, n2 in node_pairs:
			reached_target = n2 == path[-1]
			hop = self.lnhopgraph[n1][n2]["hop"]
			direction = dir0 if n1 < n2 else dir1
			probe_passed = hop.probe(direction, amount)
			if not probe_passed:
				break
		#print("probe reached_target?", reached_target)
		return reached_target


	def probe_hop(self, target_node_pair, bs, jamming, max_failed_probes_per_hop=10, best_dir_chance=0.75):
		'''
			Probe a given target hop (in general, with multiple probes along different paths).

			Parameters:
			- target_node_pair: a pair of node IDs defining the target hop
			- bs: specify probe amount choice method
			- jamming: use jamming-enhanced probing after "regular" probing
			- max_failed_probes_per_hop: stop probing the hop is this many probes didn't reach it
			- best_dir_chance: choosing between two possible directions, flip a coin biased in favor of "best" direction

			Return:
			- num_probes: how many probes were made
			- reached_target: True if we ever reached the target
		'''
		target_hop = self.lnhopgraph[target_node_pair[0]][target_node_pair[1]]["hop"]
		known_failed_amount = {dir0: None, dir1: None}
		#print("\n----------------------\nProbing hop", target_node_pair)
		#print(target_hop)
		def probe_target_hop_in_direction(direction, jamming):
			'''
				Probe the target hop in a given direction, with or without jamming.

				Parameters:
				- direction: in which direction to probe
				- jamming: True if we're jamming
			'''
			made_probe, reached_target = False, False
			if target_hop.worth_probing() if jamming else target_hop.worth_probing_h_or_g(direction):
				amount = target_hop.next_a(direction, bs, jamming)
				#print("Suggest amount", amount)
				guaranteed_fail = amount >= known_failed_amount[direction] if known_failed_amount[direction] is not None else False
				if not guaranteed_fail:
					hop_direction = dir0 if target_node_pair[0] < target_node_pair[1] else dir1
					target_node_pair_in_order = target_node_pair if hop_direction == direction else reversed(target_node_pair)
					paths = self.paths_for_amount(target_node_pair_in_order, amount)
					try:
						#print("Trying next path for direction", "dir0" if direction else "dir1", ", amount:", amount)
						path = next(paths)
						reached_target = self.issue_probe_along_path(path, amount)
						made_probe = True
					except StopIteration:
						#print("Path iteration stopped for direction", "dir0" if direction else "dir1", ", amount:", amount)
						known_failed_amount[direction] = amount
				else:
					#print("Will not probe: we know NBS amount will fail")
					pass
			else:
				#print("Not worth probing")
				pass
			return made_probe, reached_target
		def choose_dir_amount_and_probe(jamming):
			'''
				Choose the NBS probing direction and amount and probe it (with multiple probes).

				Parameters:
				- jamming: True if we're jamming
			'''
			#print("choose_dir_amount_and_probe: jamming = ", jamming)
			num_probes = 0
			# this is the suggested (best) direction
			best_dir = target_hop.next_dir(bs, jamming)
			if jamming:
				available_channels_alt_dir = [i for i in target_hop.e[not best_dir] if i not in target_hop.j[not best_dir]]
				if len(available_channels_alt_dir) == 0:
					alt_dir = None
				else:
					alt_dir = not best_dir if target_hop.can_forward(not best_dir) else None 
			else:
				alt_dir = not best_dir if target_hop.worth_probing_h_or_g(not best_dir) else None
			#print("\nNext probe")
			#print("Preferred direction:", "dir0" if best_dir else "dir1")
			made_probe, reached_target = False, False
			did_probes, first_attempt = 0, True
			num_probes_failed = 0
			while not reached_target and did_probes < max_failed_probes_per_hop:
				#print("reached_target = ", reached_target)
				#print("did_probes = ", did_probes)
				# do the first attempt in the preferred direction
				if first_attempt:
					direction = best_dir
					first_attempt = False
				else:
					if alt_dir is None:
						# only one direction available
						if not made_probe:
							# we tried the only direction and didn't make a probe
							# (no paths or amount known to fail)
							# we can't do anything else
							break
						else:
							# trying the only direction once more
							direction = best_dir
					else:
						# alternative direction available
						if not made_probe:
							# didn't make a probe in this direction - try another
							if direction == best_dir:
								direction = alt_dir
							else:
								# we must have tried best direction earlier
								# if alt_dir also failed, we must stop
								break
						else:
							# can probe in either of two directions
							# choose with coin flip biased in favor of best direction
							direction = best_dir if random() < best_dir_chance else alt_dir
				made_probe, reached_target = probe_target_hop_in_direction(direction, jamming)
				if not reached_target:
					num_probes_failed += 1
				if made_probe:
					did_probes += 1
			num_probes += did_probes
			if not reached_target:
				#print("Cannot reach target hop after", num_probes, "probes")
				#print(target_node_pair, target_hop)
				pass
			return num_probes, reached_target, num_probes_failed
		total_num_probes, total_num_probes_failed = 0, 0
		while target_hop.worth_probing_h() or target_hop.worth_probing_g():
			num_probes, reached_target, probes_failed = choose_dir_amount_and_probe(jamming=False)
			total_num_probes += num_probes
			total_num_probes_failed += probes_failed
			if not reached_target:
				break
			else:
				#print("Probed successfully without jamming.")
				pass
		if jamming:
			for i in range(target_hop.N):
				target_hop.unjam(i, dir0)
				target_hop.unjam(i, dir1)
				# count jams as probes
				total_num_probes += target_hop.jam_all_except_in_direction(i, dir0)
				total_num_probes += target_hop.jam_all_except_in_direction(i, dir1)
				while target_hop.worth_probing_channel(i):
					num_probes, reached_target, num_probes_failed = choose_dir_amount_and_probe(jamming=True)
					total_num_probes += num_probes
					if not reached_target:
						break
					else:
						#print("Probed successfully with jamming.")
						pass
			target_hop.unjam_all()
		#print("Path failed", total_num_probes_failed, "times.")
		return total_num_probes


	def probe_hops(self, target_hops, bs, jamming):
		'''
			Probe a list of target hops afresh.

			Parameters:
			- target_hops: a list of target hops
			- bs: probe amount choice method
			- jamming: True if use jamming-enhanced probing after "regular" probing

			Return:
			- total_gain: total achieved informatoin gain on target hops
			- probing speed: average probing speed (bit / message) on target hops
		'''
		self.reset_all_estimates()
		def uncertainty_for_target_hops():
			return sum([self.lnhopgraph[n1][n2]["hop"].uncertainty for n1, n2 in target_hops])
		initial_uncertainty_total = uncertainty_for_target_hops()
		num_probes = sum([self.probe_hop(target_hop, bs, jamming) for target_hop in target_hops])
		final_uncertainty_total = uncertainty_for_target_hops()
		total_gain_bits = initial_uncertainty_total - final_uncertainty_total
		probing_speed = total_gain_bits / num_probes
		total_gain = total_gain_bits / initial_uncertainty_total
		return total_gain, probing_speed


	def reset_all_estimates(self):
		for n1,n2 in self.lnhopgraph.edges():
			self.lnhopgraph[n1][n2]["hop"].reset_estimates()


	def choose_target_hops_with_n_channels(self, max_num_target_hops, num_channels):
		'''
			Select target hops from the graph with a specific number of (parallel) channels.
			Note: we only consider hops that can forward in at least one direction.

			Parameters:
			- max_num_target_hops: return at most this many target hops
			  (may return fewer if there are too few hops with this many channels in the graph)
			- num_channels: the number of parallel channels in each hop

			Return: a list of target hops
		'''
		# we only choose targets that are enabled in at least one direction
		potential_target_hops = [(u,v) for u,v,e in self.lnhopgraph.edges(data=True) if (
			e["hop"].N == num_channels and (e["hop"].can_forward(dir0) or e["hop"].can_forward(dir1)))]
		shuffle(potential_target_hops)
		return potential_target_hops[:max_num_target_hops]


	def analyze_graph(self):
		'''
			Calculate some stats about capacity and structure of hops in the snapshot.
		'''
		print("\nAnalyzing graph")
		all_hops = [self.lnhopgraph.get_edge_data(n1,n2)["hop"] for (n1, n2) in self.lnhopgraph.edges()]
		def n_channel_hops(all_hops, min_N, max_N):
			return [hop for hop in all_hops if min_N <= hop.N <= max_N]
		def share_n_channel_hops(all_hops, min_N, max_N):
			return round(len(n_channel_hops(all_hops, min_N, max_N)) / len(all_hops), 4)
		def capacity(hop):
			return sum(hop.c)
		channels_in_hops = [hop.N for hop in all_hops]
		#capacity_in_hops = [capacity(hop) for hop in all_hops]
		#capacity_in_hops_btc = [c / 100000000 for c in capacity_in_hops]
		total_capacity = sum([capacity(hop) for hop in all_hops])
		#share_capacity_in_hops = [c / total_capacity for c in capacity_in_hops]
		def share_total_capacity_in_n_hops(all_hops, min_N, max_N, total_capacity):
			hops = n_channel_hops(all_hops, min_N, max_N)
			return round(sum([capacity(hop) for hop in hops]) / total_capacity, 4)
		print("Total capacity (BTC):", round(total_capacity / (100*1000*1000), 4))
		print("Maximal number of channels in a hop:", max(channels_in_hops))
		print("Share of 1-channel hops:", 		share_n_channel_hops(all_hops, 1, 1))
		print("Share of 2-channel hops:", 		share_n_channel_hops(all_hops, 2, 2))
		print("Share of 3-channel hops:", 		share_n_channel_hops(all_hops, 3, 3))
		print("Share of 4-channel hops:", 		share_n_channel_hops(all_hops, 4, 4))
		print("Share of 5-channel hops:", 		share_n_channel_hops(all_hops, 5, 5))
		print("Share of <= 5-channel hops:", 	share_n_channel_hops(all_hops, 1, 5))
		print("Share of <= 10-channel hops:", 	share_n_channel_hops(all_hops, 1, 10))
		print("Share of capacity in 1-channel hops:", share_total_capacity_in_n_hops(all_hops, 1, 1, total_capacity))
		print("Share of capacity in 2-channel hops:", share_total_capacity_in_n_hops(all_hops, 2, 2, total_capacity))
		print("Share of capacity in 3-channel hops:", share_total_capacity_in_n_hops(all_hops, 3, 3, total_capacity))
		print("Share of capacity in 4-channel hops:", share_total_capacity_in_n_hops(all_hops, 4, 4, total_capacity))
		print("Share of capacity in 5-channel hops:", share_total_capacity_in_n_hops(all_hops, 5, 5, total_capacity))
		print("Share of capacity of <= 5-channel hops:", 	share_total_capacity_in_n_hops(all_hops, 1, 5, total_capacity))
		print("Share of capacity of <= 10-channel hops:", 	share_total_capacity_in_n_hops(all_hops, 1, 10, total_capacity))

