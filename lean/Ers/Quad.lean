import Ers.Segments
import Ers.CurveData

/-!
# Quadtree equivalence (Proposition "Quadtrees") and the curve properties

The native quadtree and the `2^d`-ary tree over the Hilbert domain build the
same index because the Hilbert curve traverses every aligned sub-cube of side
`2^(n-j)` as one aligned run of `2^(d(n-j))` distances. We take that property
as the hypothesis `Aligned` and prove, for an arbitrary query set `q`:

* `src_iff`: a vertex contains `q` iff its interval contains `[min h(q), max h(q)]`,
  so both schemes' single range covers are the same vertex;
* `brc_subset_iff`: a vertex is inside `q` iff its interval is inside `h(q)`;
* `aligned_in_segments_iff` and `maximal_iff`: an interval is inside `h(q)` iff
  it is inside one Hilbert segment, and it is maximal among the intervals
  inside `h(q)` iff it is maximal among those inside its segment, so the
  union over segments of per-segment best range covers is the best range
  cover of `q`.

The hypothesis itself, together with curve-adjacency of consecutive
distances (what the segment lemma needs), is checked by `decide` for the
curves the schemes use, at orders 2 and 3 in 2D and order 2 in 3D
(`Checks`). The general case is the recursive definition of the curve.
-/


namespace Ers.Quad

open Ers.Segments

/-- The aligned interval of depth-`j` index `k` on a curve of `d·n` bits. -/
def interval (d n j k x : Nat) : Prop := k * 2 ^ (d * (n - j)) ≤ x ∧ x < (k + 1) * 2 ^ (d * (n - j))

/-- Linearisation data: a bijection between points and distances below `2^(d n)`,
and the quadtree vertices `cube j k` as sets of points. -/
structure Linearised (P : Type) (d n : Nat) where
  h : P → Nat
  hinv : Nat → P
  cube : Nat → Nat → P → Prop
  h_lt : ∀ p, h p < 2 ^ (d * n)
  left_inv : ∀ p, hinv (h p) = p
  right_inv : ∀ x, x < 2 ^ (d * n) → h (hinv x) = x
  /-- The Hilbert property: the `k`-th sub-cube at depth `j` is exactly the
  `k`-th aligned interval of length `2^(d(n-j))`. -/
  aligned : ∀ j k p, j ≤ n → (cube j k p ↔ interval d n j k (h p))

variable {P : Type} {d n : Nat} (L : Linearised P d n)

/-- Index equality: a point lies in a vertex iff its distance lies in the
vertex's interval, so both schemes store a record under corresponding labels. -/
theorem label_iff (j k : Nat) (hj : j ≤ n) (p : P) : L.cube j k p ↔ interval d n j k (L.h p) :=
  L.aligned j k p hj

/-- Single range cover: a vertex contains the query iff its interval contains the
`[min, max]` distance interval of the query. -/
theorem src_iff (q : P → Prop) (j k : Nat) (hj : j ≤ n) (plo phi : P)
    (hlo : q plo) (hhi : q phi) (hb : ∀ p, q p → L.h plo ≤ L.h p ∧ L.h p ≤ L.h phi) :
    (∀ p, q p → L.cube j k p) ↔ (∀ x, L.h plo ≤ x → x ≤ L.h phi → interval d n j k x) := by
  constructor
  · intro hcov x h1 h2
    have := (L.aligned j k plo hj).mp (hcov plo hlo)
    have := (L.aligned j k phi hj).mp (hcov phi hhi)
    simp only [interval] at *
    omega
  · intro hint p hp
    rw [L.aligned j k p hj]
    exact hint _ (hb p hp).1 (hb p hp).2

theorem interval_lt (j k x : Nat) (hj : j ≤ n) (hk : k < 2 ^ (d * j)) (hx : interval d n j k x) :
    x < 2 ^ (d * n) := by
  have h1 : (k + 1) * 2 ^ (d * (n - j)) ≤ 2 ^ (d * j) * 2 ^ (d * (n - j)) :=
    Nat.mul_le_mul_right _ hk
  have h2 : 2 ^ (d * j) * 2 ^ (d * (n - j)) = 2 ^ (d * n) := by
    rw [← Nat.pow_add]; congr 1
    have : d * j + d * (n - j) = d * (j + (n - j)) := (Nat.mul_add d j (n - j)).symm
    rw [this, Nat.add_sub_cancel' hj]
  simp only [interval] at hx
  omega

/-- Best range cover containment: a vertex lies inside the query iff its
interval lies inside the query's set of distances. -/
theorem brc_subset_iff (q : P → Prop) (j k : Nat) (hj : j ≤ n) (hk : k < 2 ^ (d * j)) :
    (∀ p, L.cube j k p → q p) ↔ (∀ x, interval d n j k x → q (L.hinv x)) := by
  constructor
  · intro hsub x hx
    apply hsub
    rw [L.aligned j k _ hj, L.right_inv x (interval_lt j k x hj hk hx)]
    exact hx
  · intro hsub p hp
    have := hsub (L.h p) ((L.aligned j k p hj).mp hp)
    rwa [L.left_inv] at this

/-! ### Transfer to Hilbert segments -/

/-- An interval of distances lies inside the query iff it lies inside one segment. -/
theorem aligned_in_segments_iff {inside : Nat → Bool} {N : Nat} {B : List Nat}
    (hB : Boundary inside N B) (lo hi : Nat) (hle : lo ≤ hi) :
    (∀ x, lo ≤ x → x ≤ hi → inside x = true) ↔
      ∃ p ∈ segments inside B, p.1 ≤ lo ∧ hi ≤ p.2 := by
  constructor
  · exact interval_subset_segment hB hle
  · rintro ⟨p, hp, h1, h2⟩ x hx1 hx2
    exact segments_sound hB p hp x (by omega) (by omega)

/-- Two segments sharing a distance are equal. -/
theorem segments_disjoint {inside : Nat → Bool} {N : Nat} {B : List Nat}
    (hB : Boundary inside N B) {p p' : Nat × Nat} (hp : p ∈ segments inside B)
    (hp' : p' ∈ segments inside B) {x : Nat} (hx : p.1 ≤ x ∧ x ≤ p.2) (hx' : p'.1 ≤ x ∧ x ≤ p'.2) :
    p = p' := by
  have hs := segments_sound hB p hp
  have hs' := segments_sound hB p' hp'
  have hm := segments_maximal hB p hp
  have hm' := segments_maximal hB p' hp'
  have h1 : p.1 = p'.1 := by
    rcases Nat.lt_trichotomy p.1 p'.1 with hlt | heq | hgt
    · exfalso
      have := hs (p'.1 - 1) (by omega) (by omega)
      rcases hm'.1 with h0 | hf
      · omega
      · simp [this] at hf
    · exact heq
    · exfalso
      have := hs' (p.1 - 1) (by omega) (by omega)
      rcases hm.1 with h0 | hf
      · omega
      · simp [this] at hf
  have h2 : p.2 = p'.2 := by
    rcases Nat.lt_trichotomy p.2 p'.2 with hlt | heq | hgt
    · exfalso
      have := hs' (p.2 + 1) (by omega) (by omega)
      simp [this] at hm
    · exact heq
    · exfalso
      have := hs (p'.2 + 1) (by omega) (by omega)
      simp [this] at hm'
  exact Prod.ext h1 h2

/-- Maximality among the intervals inside the query coincides with maximality
among the intervals inside the segment containing the interval. -/
theorem maximal_iff {inside : Nat → Bool} {N : Nat} {B : List Nat}
    (hB : Boundary inside N B) (good : Nat → Nat → Prop)
    {lo hi : Nat} (hle : lo ≤ hi) {p : Nat × Nat} (hp : p ∈ segments inside B)
    (hin : p.1 ≤ lo ∧ hi ≤ p.2) :
    (∀ lo' hi', good lo' hi' → lo' ≤ lo → hi ≤ hi' →
        (∀ x, lo' ≤ x → x ≤ hi' → inside x = true) → lo' = lo ∧ hi' = hi) ↔
      (∀ lo' hi', good lo' hi' → lo' ≤ lo → hi ≤ hi' → p.1 ≤ lo' → hi' ≤ p.2 → lo' = lo ∧ hi' = hi) := by
  constructor
  · intro hmax lo' hi' hg h1 h2 h3 h4
    exact hmax lo' hi' hg h1 h2 (fun x hx1 hx2 => segments_sound hB p hp x (by omega) (by omega))
  · intro hmax lo' hi' hg h1 h2 hall
    obtain ⟨p', hp', h1', h2'⟩ := interval_subset_segment hB (by omega) hall
    have : p = p' := segments_disjoint hB hp hp' (x := lo) ⟨hin.1, by omega⟩ ⟨by omega, by omega⟩
    subst this
    exact hmax lo' hi' hg h1 h2 h1' h2'

/-! ### Checks on the actual curves -/

namespace Checks

/-- The sub-cube of side `2^(n-j)` containing a cell. -/
def cubeId (n j : Nat) (coords : List Nat) : List Nat := coords.map (· / 2 ^ (n - j))

/-- Consecutive distances are grid-adjacent (one coordinate changes by one). -/
def adjacent (curve : List (List Nat)) : Bool :=
  (curve.zip curve.tail).all fun (a, b) =>
    ((a.zip b).map fun (x, y) => if x ≤ y then y - x else x - y).foldr (· + ·) 0 == 1

/-- Every aligned interval of length `2^(d(n-j))` is exactly one sub-cube of side `2^(n-j)`. -/
def aligned (d n : Nat) (curve : List (List Nat)) : Bool :=
  (List.range (n + 1)).all fun j =>
    let size := 2 ^ (d * (n - j))
    (List.range (curve.length / size)).all fun k =>
      let block := (curve.drop (k * size)).take size
      let id := cubeId n j (block.headD [])
      block.all (fun c => cubeId n j c == id) && ((curve.filter fun c => cubeId n j c == id).length == size)

/-- The curve is a bijection onto the grid: `2^(d n)` distinct cells. -/
def bijective (d n : Nat) (curve : List (List Nat)) : Bool :=
  curve.length == 2 ^ (d * n) && curve.eraseDups.length == curve.length

theorem curve_2d_order2 :
    adjacent CurveData.curve_2d_order2 && aligned 2 2 CurveData.curve_2d_order2 &&
      bijective 2 2 CurveData.curve_2d_order2 = true := by decide

theorem curve_2d_order3 :
    adjacent CurveData.curve_2d_order3 && aligned 2 3 CurveData.curve_2d_order3 &&
      bijective 2 3 CurveData.curve_2d_order3 = true := by decide

theorem curve_3d_order2 :
    adjacent CurveData.curve_3d_order2 && aligned 3 2 CurveData.curve_3d_order2 &&
      bijective 3 2 CurveData.curve_3d_order2 = true := by decide

end Checks

end Ers.Quad
