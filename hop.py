#! /usr/bin/python3

# Copyright (c) University of Luxembourg 2020-2021.
# Developed by Sergei Tikhomirov (sergey.s.tikhomirov@gmail.com), SnT Cryptolux group.

'''
	A model of a hop with parallel channels.
'''

from rectangle import ProbingRectangle, Rectangle

import random
from math import log2

# We encode channel direction as a boolean.
# Direction 0 is from the alphanumerically lower node ID to the higher, direction 1 is the opposite.
dir0 = True
dir1 = False

class Hop:

	def __init__(self, capacities, e_dir0, e_dir1, balances=None, granularity=1):
		'''
			Initialize a hop.
			Parameters:
			- capacities: a list of capacities
			- e_dir0: a list of indices of channels enabled in dir0
			- e_dir1: a list of indices of channels enabled in dir1
			- balances: a list of balances (if None, balances are generated randomly)
		'''
		self.N = len(capacities)
		assert(self.N > 0)
		# ensure validity of indices
		if len(e_dir0):
			assert(max(e_dir0) <= self.N)
		if len(e_dir1):
			assert(max(e_dir1) <= self.N)
		self.c = capacities
		self.e = {dir0: e_dir0, dir1: e_dir1}	# enabled
		self.j = {dir0: [], dir1: []}			# jammed
		if balances:
			# if balances are provided, check their consistency w.r.t. capacities
			assert(all(0 <= b <= c for b,c in zip(balances, capacities)))
			self.b = balances
		else:
			# for each channel, pick a balance randomly between zero and capacity
			self.b = [random.randrange(self.c[i]) for i in range(self.N)]
		# h is how much a hop can forward in dir0, if no channels are jammed
		self.h = max([b for i,b in enumerate(self.b) if i in self.e[dir0]]) if self.can_forward(dir0) else 0
		# g is how much a hop can forward in dir1, if no channels are jammed
		self.g = max([self.c[i] - b for i,b in enumerate(self.b) if i in self.e[dir1]]) if self.can_forward(dir1) else 0
		self.granularity = granularity
		self.uncertainty = None 	# will be set later
		self.reset_estimates()


	def can_forward(self, direction):
		# there is at least one channel enabled and not jammed in this direction
		return not all(i in self.j[direction] for i in self.e[direction])


	def jam(self, channel_index, direction):
		num_jams = 0
		if channel_index not in self.j[direction]:
			#print("jamming channel", channel_index, "in direction", "dir0" if direction else "dir1")
			self.j[direction].append(channel_index)
			num_jams += 1
		return num_jams


	def jam_all_except_in_direction(self, channel_index, direction):
		num_jams = 0
		for i in self.e[direction]:
			if i != channel_index:
				num_jams += self.jam(i, direction)
		return num_jams


	def unjam(self, channel_index, direction):
		if channel_index in self.j[direction]:
			#print("unjamming channel", channel_index, "in direction", "dir0" if direction else "dir1")
			self.j[direction].remove(channel_index)


	def unjam_all_in_direction(self, direction):
		for i in self.e[direction]:
			self.unjam(i, direction)


	def unjam_all(self):
		self.unjam_all_in_direction(dir0)
		self.unjam_all_in_direction(dir1)


	def get_corner_points(self):
		'''
			Get the corner points of R_u_u that are not yet excluded fro F.
			We could similarly get all points, but it's very slow.
			We use this as a shortcut to stop probing when only one point remains.

			Return: points: a list of points (each point is a list of self.N coordinates).
		'''
		R_b = Rectangle([b_l_i + 1 for b_l_i in self.b_l], self.b_u)
		R_u_u = self.R_h_u.intersect_with(self.R_g_u).intersect_with(R_b)
		R_u_l = self.R_h_u.intersect_with(self.R_g_l).intersect_with(R_b)
		R_l_u = self.R_h_l.intersect_with(self.R_g_u).intersect_with(R_b)
		ranges = [[R_u_u.l_vertex[i], R_u_u.u_vertex[i]] for i in range(len(R_u_u.l_vertex))]
		points = []
		points_left = self.S_F
		from itertools import product
		for p in product(*ranges):
			if not R_u_l.contains_point(p) and not R_l_u.contains_point(p):
				points.append(p)
				points_left -= 1
			if points_left == 0:
				break
		return points
	

	def update_dependent_hop_properties(self):
		'''
			Hop is defined by the current bounds (h_l, h_u, g_l, g_u).
			Rectangle-related properties are fully determined by these bounds.
			We set these properties here.
			This function must be called after every bound update (such as a probe).

			A ProbingRectangle has one corner either at (0, ..., 0) or at (c_1, ..., c_N).
			This holds only for hop-level bounds (obtained without probing),
			but does not hold for balance bounds (obtained with probing).
			Hence, R_b is a Rectangle, whereas all others are ProbingRectangle's.
		'''
		self.R_h_l = ProbingRectangle(self, direction = dir0, bound = self.h_l)
		self.R_h_u = ProbingRectangle(self, direction = dir0, bound = self.h_u)
		self.R_g_l = ProbingRectangle(self, direction = dir1, bound = self.g_l)
		self.R_g_u = ProbingRectangle(self, direction = dir1, bound = self.g_u)
		self.R_b   = Rectangle([b_l_i + 1 for b_l_i in self.b_l], self.b_u)
		self.S_F = self.S_F_generic(self.R_h_l, self.R_h_u, self.R_g_l, self.R_g_u, self.R_b)
		self.uncertainty = max(0, log2(self.S_F) - log2(self.granularity))
		assert(all(-1 <= self.b_l[i] <= self.b_u[i] <= self.c[i] for i in range(len(self.c)))), self
		assert(-1 <= self.h_l < self.h <= self.h_u <= max(self.c)), self
		assert(-1 <= self.g_l < self.g <= self.g_u <= max(self.c)), self
		# Assert that the true balances are inside F (as defined by the current bounds)
		b_inside_R_h_u = self.R_h_u.contains_point(self.b)
		b_inside_R_g_u = self.R_g_u.contains_point(self.b)
		b_inside_R_h_l = self.R_h_l.contains_point(self.b)
		b_inside_R_g_l = self.R_g_l.contains_point(self.b)
		b_inside_R_b   = self.R_b.contains_point(self.b)
		# B must be within the upper bounds' rectangles
		assert(b_inside_R_h_u), 		"\nB:\n" + "\n".join([str(self.b), str(self.R_h_u)])
		assert(b_inside_R_g_u), 		"\nB:\n" + "\n".join([str(self.b), str(self.R_g_u)])
		# B must be outside the lower bounds' rectangles
		assert(not b_inside_R_h_l), 	"\nB:\n" + "\n".join([str(self.b), str(self.R_h_l)])
		assert(not b_inside_R_g_l), 	"\nB:\n" + "\n".join([str(self.b), str(self.R_g_l)])
		# B must be inside the current balance bounds rectangle
		assert(b_inside_R_b), 			"\nB:\n" + "\n".join([str(self.b), str(self.R_b)])


	def reset_estimates(self):
		'''
			Set all variable hop parameters to their initial values.
			Must be called on initialization and before running repeated probing on the same hops.
		'''
		self.h_l = -1
		self.g_l = -1
		# NB: setting upper bound to max(self.c) (and not 0) is correct from the rectangle theory viewpoint
		self.h_u = max([c for (i,c) in enumerate(self.c) if i in self.e[dir0]]) if self.can_forward(dir0) else max(self.c)
		self.g_u = max([c for (i,c) in enumerate(self.c) if i in self.e[dir1]]) if self.can_forward(dir1) else max(self.c)
		self.b_l = [-1] * self.N
		self.b_u = [self.c[i] for i in range(len(self.c))]
		self.update_dependent_hop_properties()


	def __str__(self):
		s = ""
		s += "Hop with properties:\n"
		s += "  channels: " + str(self.N) + "\n"
		s += "  capacities: " + str(self.c) + "\n"
		s += "  balances: " + str(self.b) + "\n"
		s += "  enabled in dir0: " + str(self.e[dir0]) + "\n"
		s += "  enabled in dir1: " + str(self.e[dir1]) + "\n"
		s += "  jammed in dir0: " + str(self.j[dir0]) + "\n"
		s += "  jammed in dir1: " + str(self.j[dir1]) + "\n"
		s += "  h if unjammed: " + str(self.h) + "\n"
		s += "  g if unjammed: " + str(self.g) + "\n"
		def effective_h(h):
			return h if self.can_forward(dir0) else 0
		def effective_g(g):
			return g if self.can_forward(dir1) else 0
		s += "Can forward in dir0 (effective h):\n"
		s += "  " + str(effective_h(self.h_l + 1)) + " -- " + str(effective_h(self.h_u)) + "\n"
		s += "Can forward in dir1 (effective g):\n"
		s += "  " + str(effective_g(self.g_l + 1)) + " -- " + str(effective_g(self.g_u)) + "\n"
		s += "Balance estimates:\n"
		s += "  \n".join(["  " + str(self.b_l[i] + 1) + " -- " + str(self.b_u[i]) for i in range(len(self.b_l))]) + "\n"
		s += "Uncertainty: " + str(self.uncertainty) + "\n"
		return s
	

	def effective_vertex(self, direction, bound):
		'''
			The coordinate of the _effective vertex_ corresponding to bound in direction
			is determined by:

			* the bound itself (bound = amount - 1);
			* if the i-th channel is enabled;
			* if the bound is lower than the i-th capacity.

			If bound <= i-th capacity and the i-th channel is enabled,
			the effective vertex' i-th coordinate equals the bound,
			otherwise it equals the i-th capacity.

			The corresponding ProbingRectangle is determined by the effective vertex
			and either [0, ... 0] (for dir0) or [c_1, ... c_N] (for dir1).

			Parameters:

			- direction: True if the bound corresponds to a probe in dir0, False otherwise
			- bound: equals to a - 1, where a is the probing amount
			(rationale: a probe of amount a cuts the points strictly less than a).

			Return:
			- eff_vertex: an N-element vector of coordinates of the effective vertex.
		'''
		def effective_bound(bound, ch_i):
			# We're intentionally not accounting for jamming here.
			# h and g are "permanent" hop properties, assuming all channels unjammed
			# for single-channel hops, h / g bounds are not independent
			# hence, it is sufficient for channel to be enabled in one direction
			if (ch_i in self.e[direction] or self.N == 1 or bound < 0) and bound <= self.c[ch_i]:
				eff_bound = bound
			else:
				eff_bound = self.c[ch_i]
			#print("effective bound:", eff_bound)
			return eff_bound
		def effective_coordinate(bound, ch_i):
			return effective_bound(bound, ch_i) if direction == dir0 else self.c[ch_i] - effective_bound(bound, ch_i)
		eff_vertex = [effective_coordinate(bound, ch_i) for ch_i in range(self.N)]
		assert(max(eff_vertex) <= max(self.c) + 1), (eff_vertex, max(self.c))
		#print("coordinates of effective vertex for bound = ", bound, "in", ("dir0" if direction else "dir1"), ":", eff_vertex)
		return eff_vertex
	
		
	def S_F_generic(self, R_h_l, R_h_u, R_g_l, R_g_u, R_b):
		'''
			Calculate S(F) determined by five rectangles (see paper for details).
			Note: the rectangles may not correspond to the current bounds.

			We use this function to calculate both:
			- the _actual_ S(F) (using the current rectangles from self. as arguments)
			- the _potential_ S(F) if we do a probe with amount a (when doing binary search for the optimal a)

			Parameters:
			- R_h_l: a rectangle defining the     strict lower bound on h
			- R_h_u: a rectangle defining the non-strict upper bound on h
			- R_g_l: a rectangle defining the     strict lower bound on g
			- R_g_u: a rectangle defining the non-strict upper bound on g
			- R_b : a rectangle defining the current knowledge about balance bounds (only if jamming)

			Return:
			- S_F: the number of points that:
			  - belong to R_h_u and R_g_u and R_b
			  - do NOT belong to R_h_l
			  - do NOT belong to R_g_l 

			The points in S_F are all possible positions of the true balances B.

			Addition after jamming: we intersect all of involved rectangles with a new rectangle: R_b.
			R_b reflects our current knowledge about individual balance bounds.
			
		'''
		# Theoretically, we could intersect the final F with R_b,
		# but we can't do it easily because F may not be a rectangle.
		# Instead, we first intersect the four rectangles with R_b, and then derive F.
		# The end result is the same.
		R_u_u = R_h_u.intersect_with(R_g_u).intersect_with(R_b)
		R_u_l = R_h_u.intersect_with(R_g_l).intersect_with(R_b)
		R_l_u = R_h_l.intersect_with(R_g_u).intersect_with(R_b)
		R_l_l = R_h_l.intersect_with(R_g_l).intersect_with(R_b)
		'''
		print("\nR_h_l:", R_h_l, R_h_l.S())
		print("\nR_h_u:", R_h_u, R_h_u.S())
		print("\nR_g_l:", R_g_l, R_g_l.S())
		print("\nR_g_u:", R_g_u, R_g_u.S())
		print("\nR_b:\n", R_b, R_b.S())
		print("\nAfter intersecting with R_b:")
		print("\nR_u_u:", R_u_u, R_u_u.S())
		print("\nR_u_l:", R_u_l, R_u_l.S())
		print("\nR_l_u:", R_l_u, R_l_u.S())
		print("\nR_l_l:", R_l_l, R_l_l.S())
		'''
		assert(R_l_l.is_inside(R_u_u)), self
		S_F = R_u_u.S() - R_u_l.S() - R_l_u.S() + R_l_l.S()
		#print(R_u_u.S(), "-", R_u_l.S(), "-", R_l_u.S(), "+", R_l_l.S(), "=", S_F)
		assert(S_F >= 0), self
		return S_F


	def S_F_a_expected(self, direction, a):
		'''
			Calculate the _potential_ S(F) if we the probe of amount a fails ("area under the cut").
			
			Parameters:
			- direction: True if dir0, else False
			- a: the probe amount

			Return: S_F_a: the number of points in S(F) if we do a probe of amount a and it fails.
		'''
		new_b_l = [0] * len(self.b_l)
		new_b_u = self.c.copy()
		# available channels are channels that are enabled and not jammed
		available_channels = [i for i in self.e[direction] if i not in self.j[direction]]
		jamming = len(self.j[dir0]) > 0 or len(self.j[dir1]) > 0
		# mimic the scenario when probe fails
		if direction == dir0:
			new_R_h_u = self.R_h_u if jamming else ProbingRectangle(self, direction = dir0, bound = a - 1)
			new_R_g_u = self.R_g_u
			for i in available_channels:
				# probe failed => all available channels have insufficient balances
				new_b_u[i] = min(new_b_u[i], a - 1)
		else:
			new_R_h_u = self.R_h_u
			new_R_g_u = self.R_g_u if jamming else ProbingRectangle(self, direction = dir1, bound = a - 1)
			if len(available_channels) == 1:
				# we can only update the lower bound if there is only one available channel
				# and we know the probe went through this channel
				new_b_l[available_channels[0]] = max(new_b_l[available_channels[0]], self.c[available_channels[0]] - a)
		new_R_b = Rectangle(new_b_l, new_b_u)
		S_F_a = self.S_F_generic(self.R_h_l, new_R_h_u, self.R_g_l, new_R_g_u, new_R_b)
		#print("  expected area under the cut:", S_F_a, "(assuming failed probe)")
		return S_F_a


	def worth_probing_h(self):
		# is there any uncertainty left about h and can we resolve it without jamming
		return self.can_forward(dir0) and self.h_u - self.h_l > 1
	

	def worth_probing_g(self):
		# is there any uncertainty left about g and can we resolve it without jamming
		return self.can_forward(dir1) and self.g_u - self.g_l > 1


	def worth_probing_h_or_g(self, direction):
		return self.worth_probing_h() if direction == dir0 else self.worth_probing_g()


	def worth_probing_channel(self, i):
		# is it worth doing jamming-enhanced probing on this channel
		return self.b_u[i] - self.b_l[i] > 1 and (self.can_forward(dir0) or self.can_forward(dir1))


	def worth_probing(self):
		# is there any uncertainty left in the hop
		return self.uncertainty > 0


	def next_a(self, direction, naive, jamming):
		'''
			Calculate the optimal amount for probe in direction.
			The optimal amount shrinks S(F) by half.
			(In other words, the probe leaves S_F/2 under the cut.)
			We look for the optimal amount a using binary search:
			starting from the current bounds in the required direction, we choose a in the middle.
			We then check the area under the cut _if_ we probed with this amount.
			Depending on if S_F_a < S_F or S_F_a > S_F, we increase / decrease a.

			Parameters:
			- direction: True for dir0, False for dir1

			Return:
			- a: the optimal amount, or None if the hop cannot forward in this direction
		'''
		S_F_half = max(1, self.S_F // 2)
		if not jamming:
			# only makes sense to send probes between current estimates on h or g
			a_l, a_u = (self.h_l + 1, self.h_u) if direction == dir0 else (self.g_l + 1, self.g_u)
		else:
			# individual balance bounds may be outside bounds for h / g (those are bounds for maximums!)
			available_channels = [i for i in self.e[direction] if i not in self.j[direction]]
			assert(len(available_channels) == 1), "We only support probing one unjammed channel at a time"
			i = available_channels[0]
			a_l, a_u = (self.b_l[i] + 1, self.b_u[i]) if direction == dir0 else (self.c[i] - self.b_u[i], self.c[i] - self.b_l[i] - 1)
		a = (a_l + a_u + 1) // 2
		#print(a_l, a, a_u)
		#print("Naive = ", naive)
		if not naive and not jamming:
			# we only do binary search over S(F) in pre-jamming probing phase
			while True:
				S_F_a = self.S_F_a_expected(direction, a)
				#print(a_l, a, a_u)
				if S_F_a < S_F_half:
					a_l = a
				else:
					a_u = a
				new_a = (a_l + a_u + 1) // 2
				if new_a == a:
					break
				a = new_a
				#print("if a = ", a, ", then area under cut = ", S_F_a, ", need", S_F_half)
		assert(a > 0)
		return a


	def next_dir(self, naive, jamming, prefer_small_amounts=False, threshold_area_difference=0.1):
		'''
			Suggest the optimal direction for the next probe.

			Parameters:
			- naive: True if we do binary search only amounts; False if we use optimal amount choice (binary search over S(F))
			- jamming: are we doing jamming-enhanced probing after regular probing
			- prefer_small_amounts: prioritize small amounts vs cutting S(F) more precisely
			- threshold_area_difference: the difference in S(F) that we neglect when choosing between two amounts

			Return:
			- chosen_dir: the suggested direction
		'''
		assert(self.can_forward(dir0) or self.can_forward(dir1)), self
		should_consider_dir0 = jamming and self.can_forward(dir0) or not jamming and self.worth_probing_h()
		should_consider_dir1 = jamming and self.can_forward(dir1) or not jamming and self.worth_probing_g()
		if not should_consider_dir0:
			chosen_dir = dir1
		elif not should_consider_dir1:
			chosen_dir = dir0
		else:
			a_dir0 = self.next_a(dir0, naive, jamming)
			a_dir1 = self.next_a(dir1, naive, jamming)
			if naive or prefer_small_amounts:
				# choose smaller amount: more likely to pass
				chosen_dir = dir0 if a_dir0 < a_dir1 else dir1
			else:
				# prefer amount that splits in half better
				S_F_half = max(1, self.S_F // 2)
				S_F_a_dir0 = self.S_F_a_expected(dir0, a_dir0)
				S_F_a_dir1 = self.S_F_a_expected(dir1, a_dir1)
				if abs(S_F_a_dir0 - S_F_a_dir1) / S_F_half < threshold_area_difference:
					chosen_dir = dir0 if a_dir0 < a_dir1 else dir1
				else:
					chosen_dir = dir0 if abs(S_F_a_dir0 - S_F_half) < abs(S_F_a_dir1 - S_F_half) else dir1
		return chosen_dir


	def probe(self, direction, amount):
		'''
			Update the bounds as a result of a probe.

			Parameters:
			- direction: probe direction (dir0 or dir1)
			- amount: probe amount

			Return:
			- None (the current bounds are updated)
		'''
		#print("doing probe", amount, "in", "dir0" if direction else "dir1")
		jamming = len(self.j[dir0]) > 0 or len(self.j[dir1]) > 0
		#print("Are we jamming?", jamming)
		available_channels = [i for i in self.e[direction] if i not in self.j[direction]]
		if jamming:
			# if we're jamming, we must jam all channels except one
			assert(len(available_channels) <= 1)
		def b_in_dir(i, direction):
			return self.b[i] if direction == dir0 else self.c[i] - self.b[i]
		probe_passed = amount <= max(b_in_dir(i, direction) for i in available_channels)
		if direction == dir0:
			# should only update if the amount is between current bounds
			# this is not always true for intermediary hops
			should_update_h = self.h_l < amount <= self.h_u
			if probe_passed:
				#print("probe passed in dir0")
				# sic! lower bounds are strict
				if should_update_h and not jamming:
					# update hop-level lower bound
					self.h_l = amount - 1
					if len(self.e[dir0]) == 1:
						# if only one channel is enabled, we can update this channel's lower bound
						self.b_l[self.e[dir0][0]] = max(self.b_l[self.e[dir0][0]], self.h_l)
					if len(self.e[dir1]) > 0:
						# if some channels are enabled in the opposite direction, update that upper bound
						self.g_u = min(self.g_u, max(self.c[i] - self.b_l[i] for i in self.e[dir1]))
				if jamming:
					# if we're jamming, we can update the only unjammed channel's lower bound
					self.b_l[available_channels[0]] = max(self.b_l[available_channels[0]], amount - 1)
			else:
				#print("probe failed in dir0")
				if should_update_h and not jamming:
					# update hop-level upper bound
					self.h_u = amount - 1
					for i in self.e[dir0]:
						# update all channels' upper bounds
						self.b_u[i] = min(self.b_u[i], self.h_u)
					if len(self.e[dir1]) > 0:
						# if some channels are enabled in the opposite direction, update their lower bound
						self.g_l = max(self.g_l, min(self.c[i] - self.b_u[i] - 1 for i in self.e[dir1]))
				if jamming:
					# if we're jamming, we can update the only unjammed channel's upper bound
					self.b_u[available_channels[0]] = min(self.b_u[available_channels[0]], amount - 1)
		else:
			should_update_g = self.g_l < amount <= self.g_u
			if probe_passed:
				#print("probe passed in dir1")
				if should_update_g and not jamming:
					self.g_l = amount - 1
					if len(self.e[dir1]) == 1:
						self.b_u[self.e[dir1][0]] = min(self.b_u[self.e[dir1][0]], 
							self.c[self.e[dir1][0]] - self.g_l - 1)
					if len(self.e[dir0]) > 0:
						self.h_u = min(self.h_u, max(self.b_u[i] for i in self.e[dir0]))
				if jamming:
					self.b_u[available_channels[0]] = min(self.b_u[available_channels[0]],
						self.c[available_channels[0]] - amount)
			else:
				#print("probe failed in dir1")
				if should_update_g and not jamming:
					self.g_u = amount - 1
					for i in self.e[dir1]:
						self.b_l[i] = max(self.b_l[i], self.c[i] - self.g_u - 1)
					if len(self.e[dir0]) > 0:
						self.h_l = max(self.h_l, min(self.b_l[i] for i in self.e[dir0]))
				if jamming:
					self.b_l[available_channels[0]] = max(self.b_l[available_channels[0]], 
						self.c[available_channels[0]] - amount)
		#print("after probe:", self.h_l, self.h_u, self.g_l, self.g_u)
		self.update_dependent_hop_properties()
		if self.uncertainty == 0:
			corner_points = self.get_corner_points()
			assert(len(corner_points) <= 1)
			if len(corner_points) == 1:
				p = corner_points[0]
				for i in range(self.N):
					if self.worth_probing_channel(i):
						self.b_l[i] = p[i] - 1
						self.b_u[i] = p[i]
				if len(self.e[dir0]) > 0:
					self.h_l = max(self.h_l, min([p[i] for i in self.e[dir0]]) - 1)
					self.h_u = min(self.h_u, max([p[i] for i in self.e[dir0]]))
				if len(self.e[dir1]):
					self.g_l = max(self.g_l, min([self.c[i] - p[i] for i in self.e[dir1]]) - 1)
					self.g_u = min(self.g_u, max([self.c[i] - p[i] for i in self.e[dir1]]))
			else:
				print("Corners are not viable points, continue probing")
				pass
			self.update_dependent_hop_properties()
		return probe_passed

