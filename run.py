#! /usr/bin/python3

'''
This file is part of Lightning Network Probing Simulator.

Copyright © 2020-2021 University of Luxembourg

	Permission is hereby granted, free of charge, to any person obtaining a copy
	of this software and associated documentation files (the "Software"), to deal
	in the Software without restriction, including without limitation the rights
	to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
	copies of the Software, and to permit persons to whom the Software is
	furnished to do so, subject to the following conditions:

	The above copyright notice and this permission notice shall be included in all
	copies or substantial portions of the Software.

	THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
	IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
	FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
	AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
	LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
	OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
	SOFTWARE.

SPDX-FileType: SOURCE
SPDX-FileCopyrightText: 2020-2021 University of Luxembourg
SPDX-License-Identifier: MIT
'''

import argparse
import time

from experiments import experiment_1, experiment_2
from prober import Prober


SNAPSHOT_FILENAME = "./snapshots/listchannels-2021-12-09.json"
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
# very high-dimensional hops are rare in snapshots - too few to run experiments on
MAX_MAX_NUM_CHANNELS = 5

def main():
	parser = argparse.ArgumentParser()
	parser.add_argument("--num_target_hops", default=100, type=int,
		help="The number of target hops per experiment run.")
	parser.add_argument("--num_runs_per_experiment", default=10, type=int,
		help="Run the same experiment this many times (results are averaged).")
	parser.add_argument("--min_num_channels", default=1, type=int,
		help="Consider target hops with the number of channels from this number.")
	parser.add_argument("--max_num_channels", default=5, type=int,
		help="Consider target hops with the number of channels up to this number.")
	parser.add_argument("--use_snapshot", dest="use_snapshot", action="store_true",
		help="Pick target hops from snapshot? (Then do both direct and remote probing.)")
	#parser.add_argument("--jamming", dest="jamming", action="store_true",
	#	help="Use jamming after h and g are known?")
	args = parser.parse_args()

	if args.use_snapshot and args.max_num_channels > MAX_MAX_NUM_CHANNELS:
		print("Too high max_num_channels: snapshot doesn't have that many hops with that many channels.")
		exit()

	prober = Prober(SNAPSHOT_FILENAME, "PROBER", ENTRY_NODES, ENTRY_CHANNEL_CAPACITY) if args.use_snapshot else None
	
	if prober:
		prober.analyze_graph()

	experiment_1(prober, args.num_target_hops, args.num_runs_per_experiment, 
		args.min_num_channels, args.max_num_channels)#, args.use_snapshot, args.jamming)
	experiment_2(args.num_target_hops, args.num_runs_per_experiment)


if __name__ == "__main__":
	start_time = time.time()
	main()
	end_time = time.time()
	print("Completed in", round(end_time - start_time), "seconds.")
