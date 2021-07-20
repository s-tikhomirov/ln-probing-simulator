#! /usr/bin/python3

# Copyright (c) University of Luxembourg 2020-2021.
# Developed by Sergei Tikhomirov (sergey.s.tikhomirov@gmail.com), SnT Cryptolux group.


from hop import Hop, dir0, dir1
from graph import create_multigraph_from_snapshot, ln_multigraph_to_hop_graph

import networkx as nx
import random


class Prober:

	def __init__(self, snapshot_filename, node_id, entry_nodes, entry_channel_capacity, granularity=1):
		'''
			Initialize a LN user model.

			Parameters:
			- ln: the LN model
			- node_id: the user's node ID
		'''
		self.our_node_id = node_id
		ln_multigraph = create_multigraph_from_snapshot(snapshot_filename)
		self.lnhopgraph = ln_multigraph_to_hop_graph(ln_multigraph)
		for entry_node in entry_nodes:
			self.open_channel(self.our_node_id, entry_node, entry_channel_capacity)
			#print("Added hop:\n", self.lnhopgraph[self.our_node_id][entry_node]["hop"])
		self.local_routing_graph = self.lnhopgraph.to_directed()
		'''
		def directed_edge_can_forward(u, v):
			hop = self.lnhopgraph[u][v]["hop"]
			return hop.can_forward(dir0) if u < v else hop.can_forward(dir1)

		edges_to_remove = [(u,v) for u,v in self.local_routing_graph.edges() if not directed_edge_can_forward(u,v) ]
		print("Total edges in routing graph:", len(self.local_routing_graph.edges()))
		print("Edges to remove:", len(edges_to_remove))
		self.local_routing_graph.remove_edges_from(edges_to_remove)
		'''


	def hop_to_string(self, first, second):
		return str(self.lnhopgraph[first][second]["hop"])


	def __str__(self):
		return "\n".join([self.hop_to_string(first, second) for first, second in self.lnhopgraph.edges()])


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
			#print("Old hop:", hop)
			capacities = hop.c.append(capacity)
			e_dir0 = hop.e[dir0].append(direction)
			e_dir1 = hop.e[dir0].append(not direction)
			balances = hop.balances.append(balance_at_first)
			updated_hop = Hop(capacities, e_dir0, e_dir1, balances)
			#print("Updated hop:", updated_hop)
			self.lnhopgraph[first][second]["hop"] = updated_hop
		else:
			self.lnhopgraph.add_edge(first, second)
			e_dir0 = [0] if direction == dir0 else []
			e_dir1 = [0] if direction == dir1 else []
			self.lnhopgraph[first][second]["hop"] = Hop([capacity], e_dir0, e_dir1, [balance_at_first])


	def filtered_routing_graph_for_amount(self, amount, exclude_nodes):
		'''
			Create a filtered directed routing graph.

			For faster routing, we should discard edges that we know cannot forward the required amount.
			Such filtered graph is created for each routing (it's a graph view, no data is copied).
			An alternative approach would be to create routes on the full graph
			  and discard those that contain low-balance edges.
		'''
		def filter_edge(n1, n2):
			'''
				Return True for edges to be included in the filtered graph.
				We include edges that (theoretically) can forward the amount (i.e., their upper bound is not lower than amount).
			'''
			hop = self.lnhopgraph[n1][n2]["hop"]
			direction = dir0 if n1 < n2 else dir1
			if direction == dir0:
				return hop.can_forward(dir0) and amount < hop.h_u
			else:
				return hop.can_forward(dir1) and amount < hop.g_u

		def filter_node(n):
			'''
				Return True for nodes to be included in the filtered graph.
				A generic User generally shouldn't exclude nodes.
				A Prober, however, excludes the target node and calculates routes to the previous node
				  to ensure the route includes the target hop as the last hop.
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


	def uncertainty_for_hop(self, n1, n2):
		return self.lnhopgraph[n1][n2]["hop"].uncertainty


	def uncertainty_for_hops(self, hops):
		return sum([self.uncertainty_for_hop(n1, n2) for n1, n2 in hops])


	def issue_probe_along_path(self, path, amount):
		assert(path[0] == self.our_node_id)
		# don't probe our own channels
		node_pairs = [p for p in zip(path, path[1:])]
		reached_target = False
		for n1, n2 in node_pairs:
			reached_target = n2 == path[-1]
			#print("----probing intermediary? hop between", n1, "and", n2)
			hop = self.lnhopgraph[n1][n2]["hop"]
			probe_passed = hop.probe(direction = dir0 if n1 < n2 else dir1, amount = amount)
			if not probe_passed:
				break
		#print("probe reached_target?", reached_target)
		return reached_target


	def probe_hop(self, target_node_pair, naive, jamming, max_failed_probes_per_hop=20, best_dir_chance=0.5):
		target_hop = self.lnhopgraph[target_node_pair[0]][target_node_pair[1]]["hop"]
		known_failed = {dir0: None, dir1: None}
		print("\n\n----------------------\nProbing hop", target_node_pair)
		def probe_hop_in_direction(target_node_pair, direction, jamming):
			#print("probe_hop_in_direction: jamming = ", jamming)
			# should check if jammed
			#print("Probing in direction", "dir0" if direction else "dir1")
			made_probe, reached_target = False, False
			worth_probing = target_hop.worth_probing() if jamming else target_hop.worth_probing_h_or_g(direction)
			if worth_probing:
				amount = target_hop.next_a(direction, naive, jamming)
				#print("Suggest amount", amount)
				if (amount < known_failed[direction] if known_failed[direction] is not None else True):
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
						known_failed[direction] = amount
				else:
					print("Will not probe: we know optimal amount will fail")
					pass
			else:
				print("Not worth probing")
				pass
			return made_probe, reached_target
		def choose_dir_amount_and_probe(jamming):
			#print("choose_dir_amount_and_probe: jamming = ", jamming)
			num_probes = 0
			best_dir = target_hop.next_dir(naive, jamming)
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
							direction = best_dir if random.random() < best_dir_chance else alt_dir
				made_probe, reached_target = probe_hop_in_direction(target_node_pair, direction, jamming)
				if made_probe:
					did_probes += 1
			num_probes += did_probes
			if not reached_target:
				print("Cannot reach target hop after", num_probes, "probes")
				#print(target_node_pair, target_hop)
			return num_probes, reached_target

		total_num_probes = 0
		while target_hop.worth_probing_h() or target_hop.worth_probing_g():
			num_probes, reached_target = choose_dir_amount_and_probe(jamming=False)
			total_num_probes += num_probes
			if not reached_target:
				break
			else:
				print("Probed successfully without jamming.")
				pass
		if jamming:
			for i in range(target_hop.N):
				target_hop.unjam(i, dir0)
				target_hop.unjam(i, dir1)
				# count jams as probes
				total_num_probes += target_hop.jam_all_except_in_direction(i, dir0)
				total_num_probes += target_hop.jam_all_except_in_direction(i, dir1)
				while target_hop.worth_probing_channel(i):
					num_probes, reached_target = choose_dir_amount_and_probe(jamming=True)
					total_num_probes += num_probes
					if not reached_target:
						break
					else:
						print("Probed successfully with jamming.")
						pass
			target_hop.unjam_all()
		return total_num_probes


	def probe_hops(self, target_hops, naive, jamming):
		self.reset_all_hops()
		initial_uncertainty_total = self.uncertainty_for_hops(target_hops)
		num_probes = sum([self.probe_hop(target_hop, naive, jamming) for target_hop in target_hops])
		final_uncertainty_total = self.uncertainty_for_hops(target_hops)
		total_gain_bits = initial_uncertainty_total - final_uncertainty_total
		probing_speed = total_gain_bits / num_probes
		total_gain = total_gain_bits / initial_uncertainty_total
		return total_gain, probing_speed


	def reset_all_hops(self):
		for n1,n2 in self.lnhopgraph.edges():
			self.lnhopgraph[n1][n2]["hop"].reset_estimates()


	def choose_target_hops_with_n_channels(self, max_num_target_hops, num_channels):
		# we only choose targets that are enabled in at least one directions
		potential_target_hops = [(u,v) for u,v,e in self.lnhopgraph.edges(data=True) if (
			e["hop"].N == num_channels and (e["hop"].can_forward(dir0) or e["hop"].can_forward(dir1)))]
		random.shuffle(potential_target_hops)
		return potential_target_hops[:max_num_target_hops]


	def analyze_graph(self):
		print("Analyzing graph")
		all_hops = [self.lnhopgraph.get_edge_data(n1,n2)["hop"] for (n1, n2) in self.lnhopgraph.edges()]
		def n_channel_hops(all_hops, min_N, max_N):
			return [hop for hop in all_hops if min_N <= hop.N <= max_N]
		def share_n_channel_hops(all_hops, min_N, max_N):
			return len(n_channel_hops(all_hops, min_N, max_N)) / len(all_hops)
		def capacity(hop):
			return sum(hop.c)
		channels_in_hops = [hop.N for hop in all_hops]
		#capacity_in_hops = [capacity(hop) for hop in all_hops]
		#capacity_in_hops_btc = [c / 100000000 for c in capacity_in_hops]
		total_capacity = sum([capacity(hop) for hop in all_hops])
		#share_capacity_in_hops = [c / total_capacity for c in capacity_in_hops]
		def share_total_capacity_in_n_hops(all_hops, min_N, max_N, total_capacity):
			hops = n_channel_hops(all_hops, min_N, max_N)
			return sum([capacity(hop) for hop in hops]) / total_capacity
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

