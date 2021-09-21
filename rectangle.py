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

'''
	Rectangles (N-dimensional cuboids) that describe sets of points where the true balances may or may not be.
	See the paper for details.
'''

import operator
from functools import reduce


class Rectangle():
	'''
		A generic rectangle is defined by two opposing vertices: the lower and the upper.
		All coordinates of the lower vertex are less than or equal to than of the upper vertex.
	'''

	def __init__(self, l_vertex, u_vertex):
		'''
			Initialize a rectangle.

			Parameters:
			l_vertex: the lower-left vertex
			u_vertex: the upper-right vertex
		'''
		if l_vertex and u_vertex:
			assert(len(l_vertex) == len(u_vertex))
			# if at at least one dimension l_vertex is higher than u_vertes, the rectangle is empty
			self.is_empty = not all(coord_l <= coord_u for coord_l, coord_u in zip(l_vertex, u_vertex))
			self.l_vertex = None if self.is_empty else l_vertex
			self.u_vertex = None if self.is_empty else u_vertex
		else:
			self.is_empty = True
			self.l_vertex = None
			self.u_vertex = None


	def S(self):
		'''
			Calculate the area of the rectangle.
			The area of a rectangle is the product of the widths of its sides.
			All boundaries are inclusive.
		'''
		if self.is_empty:
			return 0
		else:
			widths = [max(0, coord_u - coord_l + 1) for coord_l, coord_u in zip(self.l_vertex, self.u_vertex)]
			return reduce(operator.mul, widths, 1)


	def __str__(self):
		s = "\n"
		if self.is_empty:
			s = "\nEmpty figure"
		else:
			s += "Rectangle with vertices:\n"
			s += str(self.l_vertex) + "\n"
			s += str(self.u_vertex)
		return s


	def contains_point(self, point):
		'''
			Return True if a given point is inside the rectangle, False otherwise.
		'''
		if not self.is_empty and point is not None:
			assert(len(point) == len(self.l_vertex))
			lcond = all(l <= p for l,p in zip(self.l_vertex, point))
			ucond = all(p <= u for p,u in zip(point, self.u_vertex))
			return lcond and ucond
		return False


	def is_inside(self, other_rectangle):
		'''
			Check if this rectangle is inside another rectangle.

			Parameters:
			- other_rectangle: the other ("outside") rectangle

			Return:
			- True if this rectangle (self) is fully inside other_rectangle
		'''
		if self.is_empty:
			# empty rectangle is inside any rectangle
			return True
		elif other_rectangle.is_empty:
			# any non-empty rectangle is not inside an empty rectangle
			return False
		else:
			assert(len(self.l_vertex) == len(other_rectangle.l_vertex))
			return all((self.l_vertex[i] >= other_rectangle.l_vertex[i] and 
				self.u_vertex[i] <= other_rectangle.u_vertex[i]) for i in range(len(self.l_vertex)))


	def intersect_with(self, other_rectangle):
		'''
			Intersect self with another rectangle.
			An intersection of two rectangles is a rectangle.

			Parameters:
			- other_rectangle: the other rectangle

			Return:
			- the intersection Rectangle or EmptyRectangle if the intersection is empty

		'''
		if self.is_empty or other_rectangle.is_empty:
			# anything intersected with empty figure is empty
			return EmptyRectangle()
		assert(len(self.l_vertex) == len(other_rectangle.l_vertex))
		N = len(self.l_vertex)
		intersection_l_vertex = [None] * N
		intersection_u_vertex = [None] * N
		# iterate through all dimensions
		for i in range(N):
			if (self.l_vertex[i] > other_rectangle.u_vertex[i] or 
				self.u_vertex[i] < other_rectangle.l_vertex[i]):
				# no intersection along one dimension => intersection is empty
				return EmptyRectangle()
			else:
				# otherwise, l is max of l's, u is min of u's
				intersection_l_vertex[i] = max(self.l_vertex[i], other_rectangle.l_vertex[i])
				intersection_u_vertex[i] = min(self.u_vertex[i], other_rectangle.u_vertex[i])
		return Rectangle(intersection_l_vertex, intersection_u_vertex)



class ProbingRectangle(Rectangle):
	'''
		A rectangle corresponding to a probe without jamming.
		If dir0, the lower-left vertex is [0, ... 0].
		If dir1, the upper-right vertex is [c1, ..., cN].
		The other vertex is determined by the effective probe amount along the respective dimension.
	'''
	def __init__(self, hop, direction, bound):
		# bound = amount - 1 (it makes all rectangles' borders inclusive)
		vertex = hop.effective_vertex(direction, bound)
		l_vertex, u_vertex = ([0] * hop.N, vertex) if direction else (vertex, hop.c)
		Rectangle.__init__(self, l_vertex, u_vertex)


class EmptyRectangle(Rectangle):
	'''
		An empty figure (with area 0).
	'''
	def __init__(self):
		Rectangle.__init__(self, None, None)

