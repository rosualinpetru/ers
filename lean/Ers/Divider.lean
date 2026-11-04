/-!
# The mass-based TDAG (Lemma "Mass-based TDAG")

A divider maps a canonical interval to its children. The lemma is proved for
*any* divider that is `Good`: children are strictly shorter sub-intervals, the
children of a non-singleton interval cover it, and a single cell is never
divided. (The test suite checks the implemented divider against exactly these
three properties on random data.) The definition `vertices` being accepted by
Lean *is* the termination claim: the recursion is well founded on the length.
`depth_le` bounds the depth by the domain size, `cell_is_vertex` says every
cell is a (leaf) vertex, and `src_exists_unique` says the single range cover
returns exactly one vertex, the shortest one containing the query.
-/

namespace Ers.Divider

/-- A canonical interval `[lo, hi]`, inclusive. -/
structure Iv where
  lo : Nat
  hi : Nat
deriving DecidableEq, Repr

namespace Iv
def len (v : Iv) : Nat := v.hi + 1 - v.lo
def contains (v : Iv) (x : Nat) : Prop := v.lo ≤ x ∧ x ≤ v.hi
/-- `v.sub w`: `v ⊆ w`. -/
def sub (v w : Iv) : Prop := w.lo ≤ v.lo ∧ v.hi ≤ w.hi
instance : DecidableRel sub := fun _ _ => inferInstanceAs (Decidable (_ ∧ _))
end Iv

/-- A division strategy. -/
structure Divider where
  divide : Iv → List Iv

/-- The properties of the mass-based (and uniform) TDAG dividers. -/
structure Divider.Good (D : Divider) : Prop where
  strict : ∀ v w, w ∈ D.divide v → w.sub v ∧ w.len < v.len ∧ w.lo ≤ w.hi
  cover : ∀ v, v.lo < v.hi → ∀ x, v.contains x → ∃ w ∈ D.divide v, w.contains x
  leaf : ∀ v, v.lo = v.hi → D.divide v = []

variable {D : Divider}

/-- Every vertex reachable from `v` (with repetitions; sharing is a memoisation
detail that does not affect the set). Accepted by Lean because every child is
strictly shorter: the construction terminates. -/
def vertices (hD : D.Good) (v : Iv) : List Iv :=
  v :: (D.divide v).attach.flatMap (fun ⟨w, hw⟩ => vertices hD w)
termination_by v.len
decreasing_by exact (hD.strict v w hw).2.1

/-- Depth of the structure below `v`. -/
def depth (hD : D.Good) (v : Iv) : Nat :=
  1 + ((D.divide v).attach.map (fun ⟨w, hw⟩ => depth hD w)).foldr max 0
termination_by v.len
decreasing_by exact (hD.strict v w hw).2.1

theorem foldr_max_le {l : List Nat} {b : Nat} (h : ∀ x ∈ l, x ≤ b) : l.foldr max 0 ≤ b := by
  induction l with
  | nil => simp
  | cons x xs ih =>
    simp only [List.foldr_cons]
    have hx := h x (List.mem_cons_self ..)
    have := ih (fun y hy => h y (List.mem_cons_of_mem _ hy))
    omega

/-- The depth is at most the number of cells of the root interval. -/
theorem depth_le (hD : D.Good) (v : Iv) (hv : v.lo ≤ v.hi) : depth hD v ≤ v.len := by
  rw [depth]
  have hchild : ∀ x ∈ (D.divide v).attach.map (fun ⟨w, hw⟩ => depth hD w), x ≤ v.len - 1 := by
    intro x hx
    obtain ⟨⟨w, hw⟩, -, rfl⟩ := List.mem_map.mp hx
    show depth hD w ≤ v.len - 1
    have hs := hD.strict v w hw
    have := depth_le hD w hs.2.2
    omega
  have := foldr_max_le hchild
  have : 1 ≤ v.len := by simp [Iv.len]; omega
  omega
termination_by v.len
decreasing_by exact (hD.strict v w hw).2.1

/-- Every vertex reachable from `v` is a sub-interval of `v`. -/
theorem vertices_sub (hD : D.Good) (v : Iv) : ∀ w ∈ vertices hD v, w.sub v := by
  intro w hw
  rw [vertices] at hw
  rcases List.mem_cons.mp hw with rfl | hw
  · exact ⟨Nat.le_refl _, Nat.le_refl _⟩
  · simp only [List.mem_flatMap, List.mem_attach, true_and, Subtype.exists] at hw
    obtain ⟨u, hu, hwu⟩ := hw
    have h1 := vertices_sub hD u w hwu
    have h2 := (hD.strict v u hu).1
    exact ⟨Nat.le_trans h2.1 h1.1, Nat.le_trans h1.2 h2.2⟩
termination_by v.len
decreasing_by exact (hD.strict v u hu).2.1

/-- Every cell of `v` is a leaf vertex of the structure below `v`. -/
theorem cell_is_vertex (hD : D.Good) (v : Iv) : ∀ x, v.contains x → (⟨x, x⟩ : Iv) ∈ vertices hD v := by
  intro x hx
  rw [vertices]
  rcases Nat.lt_or_ge v.lo v.hi with hlt | hge
  · obtain ⟨w, hw, hwx⟩ := hD.cover v hlt x hx
    apply List.mem_cons_of_mem
    simp only [List.mem_flatMap, List.mem_attach, true_and, Subtype.exists]
    exact ⟨w, hw, cell_is_vertex hD w x hwx⟩
  · have : v = ⟨x, x⟩ := by
      obtain ⟨h1, h2⟩ := hx
      cases v; simp at *; omega
    subst this
    exact List.mem_cons_self ..
termination_by v.len
decreasing_by exact (hD.strict v w hw).2.1

/-- The shortest element of a non-empty list. -/
def pickMin : List Iv → Option Iv
  | [] => none
  | v :: vs =>
    match pickMin vs with
    | none => some v
    | some m => if v.len ≤ m.len then some v else some m

theorem pickMin_cons_ne_none (v : Iv) (vs : List Iv) : pickMin (v :: vs) ≠ none := by
  simp only [pickMin]
  cases pickMin vs with
  | none => simp
  | some m => by_cases h : v.len ≤ m.len <;> simp [h]

theorem pickMin_spec : ∀ l : List Iv, ∀ m, pickMin l = some m → m ∈ l ∧ ∀ w ∈ l, m.len ≤ w.len := by
  intro l
  induction l with
  | nil => intro m h; simp [pickMin] at h
  | cons v vs ih =>
    intro m h
    cases hrec : pickMin vs with
    | none =>
      have hnil : vs = [] := by
        cases vs with
        | nil => rfl
        | cons u us => exact absurd hrec (pickMin_cons_ne_none u us)
      subst hnil
      simp [pickMin] at h; subst h
      exact ⟨List.mem_cons_self .., fun w hw => by simp at hw; subst hw; exact Nat.le_refl _⟩
    | some m' =>
      simp only [pickMin, hrec] at h
      obtain ⟨hm', hmin⟩ := ih m' hrec
      by_cases hle : v.len ≤ m'.len
      · simp [hle] at h; subst h
        refine ⟨List.mem_cons_self .., ?_⟩
        intro w hw
        rcases List.mem_cons.mp hw with rfl | hw
        · exact Nat.le_refl _
        · exact Nat.le_trans hle (hmin w hw)
      · simp [hle] at h; subst h
        refine ⟨List.mem_cons_of_mem _ hm', ?_⟩
        intro w hw
        rcases List.mem_cons.mp hw with rfl | hw
        · omega
        · exact hmin w hw

theorem pickMin_some : ∀ l : List Iv, l ≠ [] → ∃ m, pickMin l = some m := by
  intro l hl
  cases l with
  | nil => exact absurd rfl hl
  | cons v vs =>
    cases h : pickMin (v :: vs) with
    | none => exact absurd h (pickMin_cons_ne_none v vs)
    | some m => exact ⟨m, rfl⟩

/-- The single range cover: the shortest vertex containing the query. -/
def src (hD : D.Good) (root q : Iv) : Option Iv :=
  pickMin ((vertices hD root).filter (fun w => decide (q.sub w)))

/-- The single range cover of a query inside the domain is exactly one vertex:
it contains the query and no containing vertex is shorter. -/
theorem src_exists_unique (hD : D.Good) (root q : Iv) (hq : q.sub root) :
    ∃ m, src hD root q = some m ∧ m ∈ vertices hD root ∧ q.sub m ∧
      ∀ w ∈ vertices hD root, q.sub w → m.len ≤ w.len := by
  have hroot : root ∈ (vertices hD root).filter (fun w => decide (q.sub w)) := by
    rw [List.mem_filter]
    refine ⟨?_, by simpa using hq⟩
    rw [vertices]; exact List.mem_cons_self ..
  have hne : (vertices hD root).filter (fun w => decide (q.sub w)) ≠ [] := by
    intro h; rw [h] at hroot; simp at hroot
  obtain ⟨m, hm⟩ := pickMin_some _ hne
  obtain ⟨hmem, hmin⟩ := pickMin_spec _ m hm
  rw [List.mem_filter] at hmem
  refine ⟨m, hm, hmem.1, by simpa using hmem.2, ?_⟩
  intro w hw hqw
  exact hmin w (List.mem_filter.mpr ⟨hw, by simpa using hqw⟩)

/-! ### Non-vacuity: the uniform binary divider is `Good` -/

/-- Halve an interval of at least two cells; leave a single cell alone. -/
def uniform : Divider where
  divide v := if v.lo < v.hi then [⟨v.lo, (v.lo + v.hi) / 2⟩, ⟨(v.lo + v.hi) / 2 + 1, v.hi⟩] else []

theorem uniform_good : uniform.Good := by
  refine ⟨?_, ?_, ?_⟩
  · intro v w hw
    simp only [uniform] at hw
    split at hw
    · simp at hw
      rcases hw with rfl | rfl <;> simp [Iv.sub, Iv.len] <;> omega
    · simp at hw
  · intro v hlt x hx
    simp only [uniform, hlt, ite_true]
    obtain ⟨h1, h2⟩ := hx
    by_cases hmid : x ≤ (v.lo + v.hi) / 2
    · exact ⟨⟨v.lo, (v.lo + v.hi) / 2⟩, by simp, h1, hmid⟩
    · exact ⟨⟨(v.lo + v.hi) / 2 + 1, v.hi⟩, by simp, by show (v.lo + v.hi) / 2 + 1 ≤ x; omega, h2⟩
  · intro v heq
    simp [uniform, heq]

end Ers.Divider
