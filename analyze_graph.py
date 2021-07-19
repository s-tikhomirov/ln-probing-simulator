#! /usr/bin/python3

# Copyright (c) University of Luxembourg 2020-2021.
# Developed by Sergei Tikhomirov (sergey.s.tikhomirov@gmail.com), SnT Cryptolux group.

from graph import create_multigraph_from_snapshot, ln_multigraph_to_hop_graph

from matplotlib import pyplot as plt
import os



snapshot_filename = "./snapshot/listchannels-2021-05-23.json"

ln_multigraph = create_multigraph_from_snapshot(snapshot_filename)
lnhopgraph = ln_multigraph_to_hop_graph(ln_multigraph)


all_hops = [lnhopgraph.get_edge_data(n1,n2)["hop"] for (n1, n2) in lnhopgraph.edges()]


def n_channel_hops(all_hops, min_N, max_N):
	return [hop for hop in all_hops if min_N <= hop.N <= max_N]

def share_n_channel_hops(all_hops, min_N, max_N):
	return len(n_channel_hops(all_hops, min_N, max_N)) / len(all_hops)

def capacity(hop):
	return sum(hop.capacities)

channels_in_hops = [hop.N for hop in all_hops]
capacity_in_hops = [capacity(hop) for hop in all_hops]
capacity_in_hops_btc = [c / 100000000 for c in capacity_in_hops]
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

LABELSIZE = 20
LEGENDSIZE = 14
TICKSIZE = 18
FIGSIZE = (12,6)
SAVE_FIGURE_TO = 'results'

plt.figure(figsize=FIGSIZE)
plt.hist(channels_in_hops, bins=max(channels_in_hops), log=True)
plt.xlabel("Number of channels in a hop", fontsize=LABELSIZE)
plt.ylabel("Number of hops", fontsize=LABELSIZE)
plt.title("A histogram of the number of channels in hops", fontsize=LABELSIZE)
#plt.tight_layout()
plt.tick_params(axis='x', labelsize=TICKSIZE)
plt.tick_params(axis='y', labelsize=TICKSIZE)
#plt.legend(fontsize=LEGENDSIZE)#, loc='best', bbox_to_anchor=(0.5, 0., 0.5, 0.5))
plt.savefig(os.path.join(SAVE_FIGURE_TO, "num_channels_in_hops.png"))
plt.clf()

plt.figure(figsize=FIGSIZE)
plt.hist(capacity_in_hops_btc, bins=100, log=True)
plt.xlabel("Total capacity of a hop (BTC)", fontsize=LABELSIZE)
plt.ylabel("Number of hops", fontsize=LABELSIZE)
plt.title("A histogram of hops by total capacity", fontsize=LABELSIZE)
#plt.tight_layout()
plt.tick_params(axis='x', labelsize=TICKSIZE)
plt.tick_params(axis='y', labelsize=TICKSIZE)
#plt.legend(fontsize=LEGENDSIZE)#, loc='best', bbox_to_anchor=(0.5, 0., 0.5, 0.5))
plt.savefig(os.path.join(SAVE_FIGURE_TO, "capacity_in_hops.png"))
plt.clf()

