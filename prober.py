#! /usr/bin/python3

# Copyright (c) University of Luxembourg 2020-2021.
# Developed by Sergei Tikhomirov (sergey.s.tikhomirov@gmail.com), SnT Cryptolux group.

from hop import Hop

import networkx as nx
import json

def create_multigraph_from_snapshot(snapshot_filename):
	print("Creating LnHopGraph from file:", snapshot_filename)
	with open(snapshot_filename, 'r') as snapshot_file:
		network = json.load(snapshot_file)
	edges_set = set()
	nodes_set = set()
	edges = []
	for channel in network["channels"]:
		cid = channel["short_channel_id"]
		source = channel["source"]
		destination = channel["destination"]
		edges.append((source, destination, cid,
			{
			"capacity": channel["satoshis"],
			"dir0_enabled": channel["dir0"]["enabled"],
			"dir1_enabled": channel["dir1"]["enabled"],
			}))
		edges_set.add(cid)
		nodes_set.add(source)
		nodes_set.add(destination)
	nodes = list(nodes_set)
	g = nx.MultiGraph()
	g.add_nodes_from(nodes)
	g.add_edges_from(edges)
	print("LN snapshot contains:", g.number_of_nodes(), "nodes,", g.number_of_edges(), "channels.")
	# continue with the largest connected component
	components = sorted(nx.connected_components(g), key=len, reverse=True)
	print("Components:", len(components), ". Continuing with the largest component.")
	def connected_component_subgraphs(G):
		# https://github.com/rkistner/chinese-postman/issues/21#issuecomment-568980233
		for c in nx.connected_components(G):
			yield G.subgraph(c)
	# create a new MultiGraph to unfreeze
	g = nx.MultiGraph(max(connected_component_subgraphs(g), key=len))
	print("LN graph created with", g.number_of_nodes(), "nodes,", g.number_of_edges(), "channels.")
	return g


def ln_multigraph_to_hop_graph(ln_multigraph):
	'''
		Generate a hopgraph from an LN multi-graph.

		Parameters:
		- ln_g: LN model multi-graph

		Return:
		- hopgraph: a non-directed graph where each edge models a hop
	'''
	hop_graph = nx.Graph()
	# initialize hop graph with nodes and empty edge attributes
	for n1, n2 in ln_multigraph.edges():
		hop_graph.add_nodes_from([n1, n2])
		hop_graph.add_edge(n1, n2)
	for n1, n2, k, d in ln_multigraph.edges(keys=True, data=True):
		multi_edge = ln_multigraph[n1][n2]
		cids = [cid for cid in multi_edge]
		capacities = []
		e_dir0 = []
		e_dir1 = []
		for i,cid in enumerate(cids):
			capacities.append(multi_edge[cid]["capacity"])
			if multi_edge[cid]["dir0_enabled"]:
				e_dir0.append(i)
			if multi_edge[cid]["dir1_enabled"]:
				e_dir1.append(i)
		hop = Hop(capacities, e_dir0, e_dir1)
		#print(hop)
		hop_graph[n1][n2]["hop"] = hop
	return hop_graph


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
			return hop.can_forward_dir0 if u < v else hop.can_forward_dir1

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
		is_dir0 = first < second
		balance_at_first = capacity if is_dir0 else 0
		if self.lnhopgraph.has_edge(first, second):
			hop = self.lnhopgraph[first][second]["hop"]
			#print("Old hop:", hop)
			capacities = hop["capacities"].append(capacity)
			e_dir0 = hop["e_dir0"].append(is_dir0)
			e_dir1 = hop["e_dir1"].append(not is_dir0)
			balances = hop["balances"].append(balance_at_first)
			updated_hop = Hop(capacities, e_dir0, e_dir1, balances)
			#print("Updated hop:", updated_hop)
			self.lnhopgraph[first][second]["hop"] = updated_hop
		else:
			self.lnhopgraph.add_edge(first, second)
			e_dir0 = [0] if     is_dir0 else []
			e_dir1 = [0] if not is_dir0 else []
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
			is_dir0 = n1 < n2
			if is_dir0:
				return hop.can_forward_dir0 and amount < hop.h_u
			else:
				return hop.can_forward_dir1 and amount < hop.g_u

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
			probe_passed = hop.probe(is_dir0 = n1 < n2, amount = amount)
			if not probe_passed:
				break
		#print("probe reached_target?", reached_target)
		return reached_target


	def probe_hop(self, target_hop, naive, max_attempts_per_direction=100):
		hop = self.lnhopgraph[target_hop[0]][target_hop[1]]["hop"]
		num_probes = 0
		no_paths = False
		#while (hop.h_u - hop.h_l > 1 and hop.g_u - hop.g_l > 1) and not no_paths:
		while hop.worth_probing() and not no_paths:
			#print("Current uncertainty:", hop.uncertainty)
			#print("Current diffs:", hop.h_u - hop.h_l, hop.g_u - hop.g_l)
			chosen_dir0 = hop.next_dir()
			amount = hop.next_a(chosen_dir0, naive)
			#print("Suggesting amount", amount, "in", "dir0" if chosen_dir0 else "dir1")
			target_hop_is_in_dir0 = target_hop[0] < target_hop[1]
			target_hop_in_order = target_hop if chosen_dir0 == target_hop_is_in_dir0 else reversed(target_hop)
			paths = self.paths_for_amount(target_hop_in_order, amount)
			reached_target = False
			num_attempts = 0
			while not (reached_target or no_paths):
				try:
					num_attempts += 1
					path = next(paths)
					reached_target = self.issue_probe_along_path(path, amount)
					num_probes += 1
				except StopIteration:
					#print("Cannot find paths to", target_hop)
					no_paths = True
					#break				
				if num_attempts > max_attempts_per_direction:
					#print("Cannot reach target after", num_attempts, "attempts")
					no_paths = True
					#break
				if no_paths:
					#print("Probing in another direction")
					alt_dir = not chosen_dir0
					if hop.worth_probing_dir(alt_dir):
						target_hop_in_order_alt = target_hop_in_order = target_hop if alt_dir == target_hop_is_in_dir0 else reversed(target_hop)
						amount_alt = hop.next_a(alt_dir, naive)
						paths_alt = self.paths_for_amount(target_hop_in_order_alt, amount_alt)
						num_attempts = 0
						while not reached_target:
							#print("trying alternative direction...")
							#import time
							#time.sleep(3)
							try:
								num_attempts += 1
								path_alt = next(paths_alt)
								reached_target = self.issue_probe_along_path(path_alt, amount_alt)
								num_probes += 1
							except StopIteration:
								#print("Cannot find paths to", target_hop)
								break				
							if num_attempts > max_attempts_per_direction:
								#print("Cannot reach target after", num_attempts, "attempts in alternative direction")
								break
		return num_probes


	def probe_hops(self, target_hops, naive):
		total_steps = 0
		for target_hop in target_hops:
			#print("\n***\nProbing target hop", target_hop)
			total_steps += self.probe_hop(target_hop, naive)
		return total_steps


	def reset_all_hops(self):
		for n1,n2 in self.lnhopgraph.edges():
			self.lnhopgraph[n1][n2]["hop"].reset()
