import Ers.Segments
import Ers.CurveData

/-!
# From the grid to the boundary hypotheses

`Segments.Boundary` assumes that the first and last distance of every run are
boundary cells of the box. This module derives that from geometry: if
consecutive curve distances are grid-adjacent cells (`Curve.adjacent`), the
curve is a bijection onto the grid, and the curve starts and ends on faces of
the domain, then the sorted list of distances of the boundary cells of any
box satisfies `Boundary`. The adjacency and bijectivity of the actual curves
are checked by `decide` in `Quad.Checks`; the start/end faces are checked in
`Checks` below. Hence Lemma "Segment decomposition" holds for the real curves
with no unproved hypothesis.
-/

namespace Ers.Geometry

open Ers.Segments

/-- A cell of a `d`-dimensional grid, as a coordinate function. -/
abbrev Cell := Nat → Nat

/-- An axis-aligned box `[lo, hi]` in `d` dimensions. -/
structure Box (d : Nat) where
  lo : Cell
  hi : Cell

namespace Box
variable {d : Nat}

def inside (q : Box d) (c : Cell) : Prop := ∀ i, i < d → q.lo i ≤ c i ∧ c i ≤ q.hi i

/-- A cell of the box with at least one coordinate on a face. -/
def boundary (q : Box d) (c : Cell) : Prop := q.inside c ∧ ∃ i, i < d ∧ (c i = q.lo i ∨ c i = q.hi i)

instance (q : Box d) (c : Cell) : Decidable (q.inside c) :=
  inferInstanceAs (Decidable (∀ i, i < d → _))
instance (q : Box d) (c : Cell) : Decidable (q.boundary c) :=
  inferInstanceAs (Decidable (_ ∧ ∃ i, i < d ∧ _))
end Box

/-- Two cells are grid-adjacent: one coordinate differs by one, the rest agree. -/
def adjacent (d : Nat) (c c' : Cell) : Prop :=
  ∃ i, i < d ∧ (c i + 1 = c' i ∨ c' i + 1 = c i) ∧ ∀ j, j < d → j ≠ i → c j = c' j

/-- Leaving a box through a grid-adjacent step means leaving from a face. -/
theorem boundary_of_exit {d : Nat} (q : Box d) {c c' : Cell}
    (hin : q.inside c) (hout : ¬ q.inside c') (hadj : adjacent d c c') : q.boundary c := by
  obtain ⟨i, hi, hstep, hrest⟩ := hadj
  refine ⟨hin, i, hi, ?_⟩
  -- the violated coordinate of c' must be i, because all others agree with c.
  have hviol : ¬ (q.lo i ≤ c' i ∧ c' i ≤ q.hi i) := by
    intro hok
    apply hout
    intro j hj
    by_cases hji : j = i
    · subst hji; exact hok
    · rw [← hrest j hj hji]; exact hin j hj
  have hci := hin i hi
  rcases hstep with h | h <;> omega

/-- A curve of `N` cells over the grid `[0, side)^d`: cell at each distance,
grid-adjacent consecutive cells, a bijection, and start and end cells on faces
of the domain. -/
structure Curve (d side N : Nat) where
  cell : Nat → Cell
  dist : Cell → Nat
  in_grid : ∀ x, x < N → ∀ i, i < d → cell x i < side
  adj : ∀ x, x + 1 < N → adjacent d (cell x) (cell (x + 1))
  left_inv : ∀ x, x < N → dist (cell x) = x
  first_on_face : ∃ i, i < d ∧ cell 0 i = 0
  last_on_face : ∃ i, i < d ∧ (cell (N - 1) i = 0 ∨ cell (N - 1) i + 1 = side)

variable {d side N : Nat} (C : Curve d side N)

/-- The query predicate on distances induced by a box. -/
def Curve.inside (q : Box d) (x : Nat) : Bool := decide (x < N ∧ q.inside (C.cell x))

/-- The sorted list of distances of the boundary cells of the box. -/
def Curve.boundaryList (q : Box d) : List Nat :=
  (List.range N).filter fun x => decide (q.boundary (C.cell x))

theorem pairwise_lt_range : ∀ n, (List.range n).Pairwise (· < ·) := by
  intro n
  induction n with
  | zero => simp
  | succ n ih =>
    rw [List.range_succ]
    apply List.pairwise_append.mpr
    refine ⟨ih, by simp, ?_⟩
    intro a ha b hb
    simp at ha hb; omega

/-- The box lies inside the grid; then a cell inside the box whose curve
neighbour is outside the box is on a face of the box, and so are the curve's
first and last cells if they are inside. -/
theorem boundary_of_curve (q : Box d) (hq : ∀ i, i < d → q.hi i < side ∧ q.lo i ≤ q.hi i) :
    Boundary (C.inside q) N (C.boundaryList q) := by
  refine ⟨?_, ?_, ?_, ?_, ?_⟩
  · exact (pairwise_lt_range N).filter _
  · intro b hb
    simp only [Curve.boundaryList, List.mem_filter, List.mem_range, decide_eq_true_eq] at hb
    simp only [Curve.inside, decide_eq_true_eq]
    exact ⟨hb.1, hb.2.1⟩
  · intro x hx
    simp only [Curve.inside, decide_eq_true_eq] at hx
    exact hx.1
  · intro x hx hstart
    simp only [Curve.inside, decide_eq_true_eq] at hx
    simp only [Curve.boundaryList, List.mem_filter, List.mem_range, decide_eq_true_eq]
    refine ⟨hx.1, hx.2, ?_⟩
    rcases hstart with h0 | hprev
    · -- the first cell of the curve is on a face of the domain, hence of the box
      subst h0
      obtain ⟨i, hi, hc⟩ := C.first_on_face
      refine ⟨i, hi, Or.inl ?_⟩
      have := hx.2 i hi
      omega
    · -- the previous cell is outside the box and adjacent
      have hx1 : x - 1 + 1 = x := by
        rcases Nat.eq_zero_or_pos x with h | h
        · subst h; simp [Curve.inside] at hprev; exact absurd hx.2 (hprev hx.1)
        · omega
      have hout : ¬ q.inside (C.cell (x - 1)) := by
        intro hin
        have : C.inside q (x - 1) = true := by simp [Curve.inside]; exact ⟨by omega, hin⟩
        simp [this] at hprev
      have hadj := C.adj (x - 1) (by omega)
      rw [hx1] at hadj
      -- adjacency is symmetric
      have hadj' : adjacent d (C.cell x) (C.cell (x - 1)) := by
        obtain ⟨i, hi, hs, hr⟩ := hadj
        exact ⟨i, hi, by omega, fun j hj hji => (hr j hj hji).symm⟩
      exact (boundary_of_exit q hx.2 hout hadj').2
  · intro x hx hnext
    simp only [Curve.inside, decide_eq_true_eq] at hx
    simp only [Curve.boundaryList, List.mem_filter, List.mem_range, decide_eq_true_eq]
    refine ⟨hx.1, hx.2, ?_⟩
    by_cases hlast : x + 1 = N
    · obtain ⟨i, hi, hc⟩ := C.last_on_face
      have hxN : x = N - 1 := by omega
      subst hxN
      have := hx.2 i hi
      have := (hq i hi)
      refine ⟨i, hi, ?_⟩
      omega
    · have hout : ¬ q.inside (C.cell (x + 1)) := by
        intro hin
        have : C.inside q (x + 1) = true := by simp [Curve.inside]; exact ⟨by omega, hin⟩
        simp [this] at hnext
      exact (boundary_of_exit q hx.2 hout (C.adj x (by omega))).2

/-! ### The actual curves start and end on faces of the domain -/

namespace Checks

def facesOK (side : Nat) (curve : List (List Nat)) : Bool :=
  (curve.headD []).any (· == 0) && (curve.getLastD []).any (fun c => c == 0 || c + 1 == side)

theorem faces_2d_order2 : facesOK 4 Ers.CurveData.curve_2d_order2 = true := by decide
theorem faces_2d_order3 : facesOK 8 Ers.CurveData.curve_2d_order3 = true := by decide
theorem faces_3d_order2 : facesOK 4 Ers.CurveData.curve_3d_order2 = true := by decide

end Checks

end Ers.Geometry
