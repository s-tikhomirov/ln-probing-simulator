#! /usr/bin/python3

# Copyright (c) University of Luxembourg 2020-2021.
# Developed by Sergei Tikhomirov (sergey.s.tikhomirov@gmail.com), SnT Cryptolux group.


from rectangle import ProbingRectangle, Rectangle

import random
from math import log2


dir0 = True
dir1 = False

class Hop:

	def __init__(self, capacities, e_dir0, e_dir1, balances=None, granularity=1):
		'''
			Initialize a hop.
			Parameters:
			- capacities: a list of capacities
			- e_dir0: indices of channels enabled in dir0
			- e_dir1: indices of channels enabled in dir1
			- balances: a list of balances (optional)
			By default, balances are generated randomly.
		'''
		self.N = len(capacities)
		assert(self.N > 0)
		# ensure validity of indices
		if len(e_dir0):
			assert(max(e_dir0) <= self.N)
		if len(e_dir1):
			assert(max(e_dir1) <= self.N)
		self.capacities = capacities
		self.e = {dir0: e_dir0, dir1: e_dir1}	# enabled
		self.j = {dir0: [], dir1: []}			# jammed
		if balances:
			# if balances are provided, check their consistency w.r.t. capacities
			assert(all(0 <= b <= c for b,c in zip(balances, capacities)))
			self.B = balances
		else:
			# for each channel, pick a balance randomly between zero and capacity
			self.B = [random.randrange(self.capacities[i]) for i in range(self.N)]
		# h is how much a hop can _really_ forward in dir0
		self.h = max([b for i,b in enumerate(self.B) if i in self.e[dir0]]) if self.can_forward(dir0) else 0
		# g is how much a hop can _really_ forward in dir1
		self.g = max([self.capacities[i] - b for i,b in enumerate(self.B) if i in self.e[dir1]]) if self.can_forward(dir1) else 0
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
		# can similarly get all points, but it's very slow
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


	def __update_dependent_hop_properties(self):
		'''
			Each of the four bounds (h_l, h_u, g_l, g_u) correspond to a rectangle.
			This function updates the rectangles to reflect the current bounds.
			It must be called after every bound update (such as a probe).
		'''
		self.R_h_l = ProbingRectangle(self, is_dir0 = True,  bound = self.h_l)
		self.R_h_u = ProbingRectangle(self, is_dir0 = True,  bound = self.h_u)
		self.R_g_l = ProbingRectangle(self, is_dir0 = False, bound = self.g_l)
		self.R_g_u = ProbingRectangle(self, is_dir0 = False, bound = self.g_u)
		self.R_b   = Rectangle([b_l_i + 1 for b_l_i in self.b_l], self.b_u)
		self.S_F = self.__S_F()
		self.uncertainty = max(0, log2(self.S_F) - log2(self.granularity))
		assert(self.h_l < self.h <= self.h_u), (self.h_l, self.h, self.h_u)
		assert(self.g_l < self.g <= self.g_u), (self.g_l, self.g, self.g_u)


	def reset_estimates(self):
		'''
			Set all variable hop parameters to their initial values.
			Must be called on initialization and before running repeated probing on the same hops.
		'''
		self.h_l = -1
		self.g_l = -1
		# FIXME: clarify the semantics here!
		self.max_c_dir_0 = max([c for (i,c) in enumerate(self.capacities) if i in self.e[dir0]]) if self.can_forward(dir0) else max(self.capacities)
		self.max_c_dir_1 = max([c for (i,c) in enumerate(self.capacities) if i in self.e[dir1]]) if self.can_forward(dir1) else max(self.capacities)
		self.h_u = self.max_c_dir_0
		self.g_u = self.max_c_dir_1
		self.b_l = [-1] * self.N
		self.b_u = [self.capacities[i] for i in range(len(self.capacities))]
		self.__update_dependent_hop_properties()


	def __str__(self):
		s = ""
		s += "Hop with properties:\n"
		s += "  channels: " + str(self.N) + "\n"
		s += "  capacities: " + str(self.capacities) + "\n"
		s += "  balances: " + str(self.B) + "\n"
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


	def __assert_hop_correct(self):
		assert(-1 <= self.h_l <= self.h_u <= self.max_c_dir_0), self
		assert(-1 <= self.g_l <= self.g_u <= self.max_c_dir_1), self
		assert(all(-1 <= self.b_l[i] <= self.b_u[i] <= self.capacities[i] for i in range(len(self.capacities)))), self
	

	def effective_vertex(self, is_dir0, bound):
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

			- is_dir0: True if the bound corresponds to a probe in dir0, False otherwise
			- bound: equals to a - 1, where a is the probing amount
			(rationale: a probe of amount a cuts the points strictly less than a).

			Return:
			- eff_vertex: an N-element vector of coordinates of the effective vertex.
		'''
		def effective_bound(bound, ch_i):
			enabled_channels = self.e[dir0] if is_dir0 else self.e[dir1]
			# sic! intentionally not accounting for jamming here
			# h and g are "permanent" hop properties, assuming all channels unjammed
			# for single-channel hops, h / g bounds are not independent
			# hence, it is sufficient for channel to be enabled in one direction
			if (ch_i in enabled_channels or self.N == 1 or bound < 0) and bound <= self.capacities[ch_i]:
				eff_bound = bound
			else:
				eff_bound = self.capacities[ch_i]
			#print("effective bound:", eff_bound)
			return eff_bound
		def effective_coordinate(bound, ch_i):
			return effective_bound(bound, ch_i) if is_dir0 else self.capacities[ch_i] - effective_bound(bound, ch_i)
		eff_vertex = [effective_coordinate(bound, ch_i) for ch_i in range(self.N)]
		assert(max(eff_vertex) <= max(self.capacities) + 1), (eff_vertex, max(self.capacities))
		#print("coordinates of effective vertex for bound = ", bound, "in", ("dir0" if is_dir0 else "dir1"), ":", eff_vertex)
		return eff_vertex
	
		
	def __S_F_generic(self, R_h_l, R_h_u, R_g_l, R_g_u, R_b):
		'''
			Calculate S(F) determined by four rectangles (see paper for details).
			Note: the rectangles don't have to correspond to the current bounds.

			We use this function to calculate both:
			- the _actual_ S(F) (using the current rectangles from self. as arguments)
			- the _potential_ S(F) if we do a probe with amount a (when doing binary search for the optimal a)

			Parameters:
			- R_h_l: a left rectangle defining the     strict lower bound on h
			- R_h_u: a left rectangle defining the non-strict upper bound on h
			- R_g_l: a left rectangle defining the     strict lower bound on g
			- R_g_u: a left rectangle defining the non-strict upper bound on g

			Return:
			- S_F: the number of points that:
			  - belong to R_h_u and R_g_u
			  - do NOT belong to R_h_l
			  - do NOT belong to R_g_l 

			The points in S_F are all possible positions of the true balances B.

			Addition after jamming: we intersect all of involved rectangles with a new rectangle: R_b.
			R_b reflects our current knowledge about individual balance bounds.
			Theoretically, we could intersect the final F with R_b
			but we can't do it easily because F may not be a rectangle.
		'''

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
		R_l_l_inside_R_u_u = R_l_l.is_inside(R_u_u)
		assert(R_l_l_inside_R_u_u), self
		
		S_F = R_u_u.S() - R_u_l.S() - R_l_u.S() + R_l_l.S()
		#print(R_u_u.S(), "-", R_u_l.S(), "-", R_l_u.S(), "+", R_l_l.S(), "=", S_F)
		assert(S_F >= 0), self
		return S_F


	def __S_F(self):
		'''
			Calculate the current S(F): the number of points balances may take as per current knowledge.
		'''
		return self.__S_F_generic(self.R_h_l, self.R_h_u, self.R_g_l, self.R_g_u, self.R_b)


	def S_F_a_expected(self, is_dir0, a):
		'''
			Calculate the _potential_ S(F) if we do a probe of amount a and it fails (aka "area under the cut").
			It doesn't matter if we assume success or failure:
			  if we find a s.t. a probe with amount a leaves S_F/2 under the cut,
			  it automatically leaves S_F/2 above the cut.
		'''
		new_b_l = [0] * len(self.b_l)
		new_b_u = self.capacities.copy()
		available_channels = [i for i in self.e[is_dir0] if i not in self.j[is_dir0]]
		jamming = len(self.j[dir0]) > 0 or len(self.j[dir1]) > 0
		# mimic the scenario when probe fails
		if is_dir0:
			new_R_h_u = self.R_h_u if jamming else ProbingRectangle(self, is_dir0 = True,  bound = a - 1)
			new_R_g_u = self.R_g_u
			for i in available_channels:
				new_b_u[i] = min(new_b_u[i], a - 1)
		else:
			new_R_h_u = self.R_h_u
			new_R_g_u = self.R_g_u if jamming else ProbingRectangle(self, is_dir0 = False, bound = a - 1)
			if len(available_channels) == 1:
				new_b_l[available_channels[0]] = max(new_b_l[available_channels[0]], self.capacities[available_channels[0]] - a)
		new_R_b = Rectangle(new_b_l, new_b_u)
		S_F_a = self.__S_F_generic(self.R_h_l, new_R_h_u, self.R_g_l, new_R_g_u, new_R_b)
		#print("  expected area under the cut:", S_F_a, "(assuming failed probe)")
		return S_F_a


	def __true_balance_is_inside_F(self):
		'''
			Check that true balances are indeed inside F,
			as defined by the current bounds
		'''
		b_inside_R_h_u = self.R_h_u.contains_point(self.B)
		b_inside_R_g_u = self.R_g_u.contains_point(self.B)
		b_inside_R_h_l = self.R_h_l.contains_point(self.B)
		b_inside_R_g_l = self.R_g_l.contains_point(self.B)
		b_inside_R_b   = self.R_b.contains_point(self.B)
		all_good = b_inside_R_h_u and b_inside_R_g_u and not b_inside_R_h_l and not b_inside_R_g_l and b_inside_R_b
		# B must be within the upper bounds' rectangles
		assert(b_inside_R_h_u), 		"\nB:\n" + "\n".join([str(self.B), str(self.R_h_u)])
		assert(b_inside_R_g_u), 		"\nB:\n" + "\n".join([str(self.B), str(self.R_g_u)])
		# B must be outside the lower bounds' rectangles
		assert(not b_inside_R_h_l), 	"\nB:\n" + "\n".join([str(self.B), str(self.R_h_l)])
		assert(not b_inside_R_g_l), 	"\nB:\n" + "\n".join([str(self.B), str(self.R_g_l)])
		# B must be inside the current balance bounds
		assert(b_inside_R_b), 			"\nB:\n" + "\n".join([str(self.B), str(self.R_b)])
		return all_good


	'''
		Functions for checking if we should continue non-enhanced probing
		(i.e., are h and g fully probed)
	'''
	def worth_probing_h(self):
		return self.can_forward(dir0) and self.h_u - self.h_l > 1
	
	def worth_probing_g(self):
		return self.can_forward(dir1) and self.g_u - self.g_l > 1

	def worth_probing_h_or_g(self, is_dir0):
		return self.worth_probing_h() if is_dir0 else self.worth_probing_g()

	def worth_probing_channel(self, i):
		return self.b_u[i] - self.b_l[i] > 1 and (self.can_forward(dir0) or self.can_forward(dir1))

	def worth_probing(self):
		return self.uncertainty > 0


	def next_a(self, is_dir0, naive, jamming):
		'''
			Calculate the optimal amount for probe in amount dir0 if is_dir0 is True, else in dir1.
			The optimal amount is the amount that decreases S(F) by half.
			(In other words, leaves S_F/2 under the cut.)
			We look for the optimal a with binary search:
			starting from the current bounds in the required direction, we choose a in the middle.
			We then check the area under the cut _if_ we probed with this amount.
			Depending on if S_F_a < S_F or S_F_a > S_F, we increase / decrease a.

			Parameters:
			- is_dir0: True to find optimal a for dir0, False for dir1

			Return:
			- a: the optimal amount, or None if the hop cannot forward in this direction
		'''
		S_F_half = max(1, self.S_F // 2)
		if not jamming:
			# only makes sense to send probes between current estimates on h or g
			a_l, a_u = (self.h_l + 1, self.h_u) if is_dir0 else (self.g_l + 1, self.g_u)
		else:
			# balance bounds may be outside bounds for h / g (those are bounds for maximums!)
			available_channels = [i for i in self.e[is_dir0] if i not in self.j[is_dir0]]
			assert(len(available_channels) == 1), "We only support probing one unjammed channel at a time"
			i = available_channels[0]
			a_l, a_u = (self.b_l[i] + 1, self.b_u[i]) if is_dir0 else (self.capacities[i] - self.b_u[i], self.capacities[i] - self.b_l[i] - 1)
		a = (a_l + a_u + 1) // 2
		#print(a_l, a, a_u)
		#print("Naive = ", naive)
		if not naive and not jamming:
			while True:
				S_F_a = self.S_F_a_expected(is_dir0, a)
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
		assert(self.can_forward(dir0) or self.can_forward(dir1)), self
		should_consider_dir0 = jamming and self.can_forward(dir0) or not jamming and self.worth_probing_h()
		should_consider_dir1 = jamming and self.can_forward(dir1) or not jamming and self.worth_probing_g()
		if not should_consider_dir0:
			chosen_dir0 = False
		elif not should_consider_dir1:
			chosen_dir0 = True
		else:
			a_dir0 = self.next_a(dir0, naive, jamming)
			a_dir1 = self.next_a(dir1, naive, jamming)
			if naive or prefer_small_amounts:
				# choose smaller amount: more likely to pass
				chosen_dir0 = a_dir0 < a_dir1
			else:
				# prefer amount that splits in half better
				S_F_half = max(1, self.S_F // 2)
				S_F_a_dir0 = self.S_F_a_expected(dir0, a_dir0)
				S_F_a_dir1 = self.S_F_a_expected(dir1, a_dir1)
				if abs(S_F_a_dir0 - S_F_a_dir1) / S_F_half < threshold_area_difference:
					chosen_dir0 = a_dir0 < a_dir1
				else:
					chosen_dir0 = abs(S_F_a_dir0 - S_F_half) < abs(S_F_a_dir1 - S_F_half)
		return chosen_dir0


	def probe(self, is_dir0, amount):
		'''
			Update the bounds as a result of a probe.

			Parameters:
			- is_dir0: probe direction: dir0 if is_dir0 = True else dir1
			- amount: probe amount

			Return:
			- None (the current bounds are updated)
		'''
		#print("before probe:", self.h_l, self.h_u, self.g_l, self.g_u)
		#print("doing probe", amount, "in", "dir0" if is_dir0 else "dir1")
		available_channels_dir0 = list(set(self.e[dir0]) - set(self.j[dir0]))
		available_channels_dir1 = list(set(self.e[dir1]) - set(self.j[dir1]))
		#print("available in dir0:", available_channels_dir0)
		#print("available in dir1:", available_channels_dir1)
		if len(self.j[dir0]) > 0 or len(self.j[dir1]) > 0:
			assert(len(available_channels_dir0) <= 1)
			assert(len(available_channels_dir1) <= 1)
		jamming = len(self.j[dir0]) > 0 or len(self.j[dir1]) > 0
		#print("Are we jamming?", jamming)
		if is_dir0:
			probe_passed = amount <= max(self.B[i] for i in available_channels_dir0)
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
						only_enabled_dir0 = self.e[dir0][0]
						self.b_l[only_enabled_dir0] = max(self.b_l[only_enabled_dir0], self.h_l)
					if len(self.e[dir1]) > 0:
						self.g_u = min(self.g_u, max(self.capacities[i] - self.b_l[i] for i in self.e[dir1]))
				if jamming:
					self.b_l[available_channels_dir0[0]] = max(self.b_l[available_channels_dir0[0]], amount - 1)
			else:
				#print("probe failed in dir0")
				if should_update_h and not jamming:
					self.h_u = amount - 1
					for i in self.e[dir0]:
						self.b_u[i] = min(self.b_u[i], self.h_u)
					if len(self.e[dir1]) > 0:
						self.g_l = max(self.g_l, min(self.capacities[i] - self.b_u[i] - 1 for i in self.e[dir1]))
				if jamming:
					self.b_u[available_channels_dir0[0]] = min(self.b_u[available_channels_dir0[0]], amount - 1)
		else:
			probe_passed = amount <= max(self.capacities[i] - self.B[i] for i in available_channels_dir1)
			should_update_g = self.g_l < amount <= self.g_u
			if probe_passed:
				#print("probe passed in dir1")
				if should_update_g and not jamming:
					self.g_l = amount - 1
					if len(self.e[dir1]) == 1:
						only_enabled_dir1 = self.e[dir1][0]
						self.b_u[only_enabled_dir1] = min(self.b_u[only_enabled_dir1], 
							self.capacities[only_enabled_dir1] - self.g_l - 1)
					if len(self.e[dir0]) > 0:
						self.h_u = min(self.h_u, max(self.b_u[i] for i in self.e[dir0]))
				if jamming:
					self.b_u[available_channels_dir1[0]] = min(self.b_u[available_channels_dir1[0]],
						self.capacities[available_channels_dir1[0]] - amount)
			else:
				#print("probe failed in dir1")
				if should_update_g and not jamming:
					self.g_u = amount - 1
					for i in self.e[dir1]:
						self.b_l[i] = max(self.b_l[i], self.capacities[i] - self.g_u - 1)
					if len(self.e[dir0]) > 0:
						self.h_l = max(self.h_l, min(self.b_l[i] for i in self.e[dir0]))
				if jamming:
					self.b_l[available_channels_dir1[0]] = max(self.b_l[available_channels_dir1[0]], 
						self.capacities[available_channels_dir1[0]] - amount)
		#print("after probe:", self.h_l, self.h_u, self.g_l, self.g_u)
		self.__update_dependent_hop_properties()
		assert(self.__true_balance_is_inside_F()), str(self.B)
		self.__assert_hop_correct()
		if self.uncertainty == 0:
			good_corner_points = self.get_corner_points()
			if len(good_corner_points) == 1:
				p = good_corner_points[0]
				#print("Found only viable corner point!", p)
				for i in range(self.N):
					if self.worth_probing_channel(i):
						self.b_l[i] = p[i] - 1
						self.b_u[i] = p[i]
				if len(self.e[dir0]) > 0:
					self.h_l = max(self.h_l, min([p[i] for i in self.e[dir0]]) - 1)
					self.h_u = min(self.h_u, max([p[i] for i in self.e[dir0]]))
				if len(self.e[dir1]):
					self.g_l = max(self.g_l, min([self.capacities[i] - p[i] for i in self.e[dir1]]) - 1)
					self.g_u = min(self.g_u, max([self.capacities[i] - p[i] for i in self.e[dir1]]))
			else:
				print("Corners are not viable points, continue probing")
				pass
			self.__update_dependent_hop_properties()
			assert(self.__true_balance_is_inside_F()), str(self.B)
			self.__assert_hop_correct()
		return probe_passed

