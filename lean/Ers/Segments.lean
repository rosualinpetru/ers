/-!
# Hilbert segments of a range query (Lemma "Segment decomposition")

After linearisation a range query is a set of curve distances. We abstract the
curve away: `inside x` says whether the cell at distance `x` lies in the query.
A *run* is a maximal set of consecutive distances that are all inside. The
boundary cells of the query are given as a sorted list `B`; the only facts
about the curve the lemma needs are the ones collected in `Boundary`:

* every boundary distance is inside the query and below the domain size;
* the first and the last distance of every run are boundary distances
  (a cell whose curve-neighbour is outside the query is adjacent, on the grid,
  to an outside cell, hence lies on a face of the box).

`segments` is Algorithm 1 of the paper at merging tolerance 0 (where the
"consecutive boundary distance" branch is subsumed by the inside test). The
theorems below say that it returns exactly the runs: every returned segment is
a run (`segments_sound`, `segments_maximal`), every inside distance is covered
(`segments_complete`), the segments start and end at boundary distances, and
there are at most `|B|` of them (`segments_length_le`). `linear_tokens` is
Proposition "Linear": the union of the segments is exactly the query's set of
distances. `interval_subset_segment` is the contiguity fact used by the
quadtree equivalence.
-/

namespace Ers.Segments

/-- The greedy segment construction over the sorted boundary list, after the first
boundary distance `s` has opened a segment that currently ends at `e`. -/
def go (inside : Nat → Bool) (s e : Nat) : List Nat → List (Nat × Nat)
  | [] => [(s, e)]
  | b :: bs => if inside (e + 1) then go inside s b bs else (s, e) :: go inside b b bs

/-- Algorithm 1 at merging tolerance 0. -/
def segments (inside : Nat → Bool) : List Nat → List (Nat × Nat)
  | [] => []
  | b :: bs => go inside b b bs

/-- What the lemma assumes about the boundary list `B` of a query over a domain
of `N` curve cells. -/
structure Boundary (inside : Nat → Bool) (N : Nat) (B : List Nat) : Prop where
  sorted : B.Pairwise (· < ·)
  mem_inside : ∀ b ∈ B, inside b = true
  inside_lt : ∀ x, inside x = true → x < N
  start_mem : ∀ x, inside x = true → (x = 0 ∨ inside (x - 1) = false) → x ∈ B
  end_mem : ∀ x, inside x = true → inside (x + 1) = false → x ∈ B

variable {inside : Nat → Bool} {N : Nat} {B : List Nat}

/-- Every run has a last distance. -/
theorem exists_run_end (hB : Boundary inside N B) :
    ∀ k x, x + k = N → inside x = true → ∃ y, x ≤ y ∧ inside y = true ∧ inside (y + 1) = false := by
  intro k
  induction k with
  | zero =>
    intro x hx hin
    have := hB.inside_lt x hin
    omega
  | succ k ih =>
    intro x hx hin
    cases hnext : inside (x + 1) with
    | false => exact ⟨x, Nat.le_refl _, hin, hnext⟩
    | true =>
      obtain ⟨y, hy, hyin, hyout⟩ := ih (x + 1) (by omega) hnext
      exact ⟨y, by omega, hyin, hyout⟩

/-- Every run has a first distance, and everything between it and any inside
distance of the run is inside. -/
theorem exists_run_start :
    ∀ x, inside x = true →
      ∃ y, y ≤ x ∧ inside y = true ∧ (y = 0 ∨ inside (y - 1) = false) ∧
        ∀ z, y ≤ z → z ≤ x → inside z = true := by
  intro x
  induction x with
  | zero =>
    intro h
    exact ⟨0, Nat.le_refl _, h, Or.inl rfl, fun z hz hz' => by
      have : z = 0 := by omega
      subst this; exact h⟩
  | succ x ih =>
    intro h
    cases hprev : inside x with
    | false =>
      refine ⟨x + 1, Nat.le_refl _, h, Or.inr (by simpa using hprev), fun z hz hz' => ?_⟩
      have : z = x + 1 := by omega
      subst this; exact h
    | true =>
      obtain ⟨y, hy, hyin, hystart, hall⟩ := ih hprev
      refine ⟨y, by omega, hyin, hystart, fun z hz hz' => ?_⟩
      rcases Nat.lt_or_ge z (x + 1) with hlt | hge
      · exact hall z hz (by omega)
      · have : z = x + 1 := by omega
        subst this; exact h

/-- The invariant of `go s e bs`: `[s, e]` is a prefix of a run that starts at
`s`, `e` is a boundary distance, and `bs` is exactly the part of `B` above `e`. -/
structure Inv (inside : Nat → Bool) (B : List Nat) (s e : Nat) (bs : List Nat) : Prop where
  s_le : s ≤ e
  run : ∀ x, s ≤ x → x ≤ e → inside x = true
  start : s = 0 ∨ inside (s - 1) = false
  e_mem : e ∈ B
  bs_sub : ∀ b ∈ bs, b ∈ B
  bs_gt : ∀ b ∈ bs, e < b
  bs_sorted : bs.Pairwise (· < ·)
  gap : ∀ b ∈ B, e < b → b ∈ bs

/-- If the run continues past `e`, it continues up to the next boundary distance. -/
theorem fill (hB : Boundary inside N B) {s e b : Nat} {bs : List Nat}
    (inv : Inv inside B s e (b :: bs)) (hnext : inside (e + 1) = true) :
    ∀ x, e ≤ x → x ≤ b → inside x = true := by
  have hb : e < b := inv.bs_gt b (List.mem_cons_self ..)
  have hmin : ∀ c ∈ b :: bs, b ≤ c := by
    intro c hc
    rcases List.mem_cons.mp hc with rfl | hc
    · exact Nat.le_refl _
    · exact Nat.le_of_lt ((List.pairwise_cons.mp inv.bs_sorted).1 c hc)
  have key : ∀ k, e + k ≤ b → inside (e + k) = true := by
    intro k
    induction k with
    | zero => intro _; exact inv.run e inv.s_le (Nat.le_refl _)
    | succ k ih =>
      intro hk
      cases k with
      | zero => simpa using hnext
      | succ k =>
        have hprev : inside (e + (k + 1)) = true := ih (by omega)
        cases hcur : inside (e + (k + 1 + 1)) with
        | true => rfl
        | false =>
          exfalso
          have hmem : e + (k + 1) ∈ B := hB.end_mem _ hprev (by simpa [Nat.add_assoc] using hcur)
          have hin : e + (k + 1) ∈ b :: bs := inv.gap _ hmem (by omega)
          have := hmin _ hin
          omega
  intro x hx hxb
  have := key (x - e) (by omega)
  rwa [show e + (x - e) = x by omega] at this

/-- If the run stops at `e`, nothing is inside before the next boundary distance. -/
theorem hole (hB : Boundary inside N B) {s e b : Nat} {bs : List Nat}
    (inv : Inv inside B s e (b :: bs)) (hnext : inside (e + 1) = false) :
    ∀ x, e < x → x < b → inside x = false := by
  have hmin : ∀ c ∈ b :: bs, b ≤ c := by
    intro c hc
    rcases List.mem_cons.mp hc with rfl | hc
    · exact Nat.le_refl _
    · exact Nat.le_of_lt ((List.pairwise_cons.mp inv.bs_sorted).1 c hc)
  have key : ∀ k, e + 1 + k < b → inside (e + 1 + k) = false := by
    intro k
    induction k with
    | zero => intro _; simpa using hnext
    | succ k ih =>
      intro hk
      have hprev : inside (e + 1 + k) = false := ih (by omega)
      cases hcur : inside (e + 1 + (k + 1)) with
      | false => rfl
      | true =>
        exfalso
        have hmem : e + 1 + (k + 1) ∈ B :=
          hB.start_mem _ hcur (Or.inr (by simpa [show e + 1 + (k + 1) - 1 = e + 1 + k by omega] using hprev))
        have hin : e + 1 + (k + 1) ∈ b :: bs := inv.gap _ hmem (by omega)
        have := hmin _ hin
        omega
  intro x hx hxb
  have := key (x - (e + 1)) (by omega)
  rwa [show e + 1 + (x - (e + 1)) = x by omega] at this

theorem inv_extend (hB : Boundary inside N B) {s e b : Nat} {bs : List Nat}
    (inv : Inv inside B s e (b :: bs)) (hnext : inside (e + 1) = true) :
    Inv inside B s b bs := by
  have hb : e < b := inv.bs_gt b (List.mem_cons_self ..)
  have hsorted := List.pairwise_cons.mp inv.bs_sorted
  have hse := inv.s_le
  refine ⟨by omega, ?_, inv.start, inv.bs_sub b (List.mem_cons_self ..), ?_, hsorted.1, hsorted.2, ?_⟩
  · intro x hsx hxb
    rcases Nat.lt_or_ge x e with hlt | hge
    · exact inv.run x hsx (Nat.le_of_lt hlt)
    · exact fill hB inv hnext x hge hxb
  · intro c hc; exact inv.bs_sub c (List.mem_cons_of_mem _ hc)
  · intro c hc hbc
    have := inv.gap c hc (by omega)
    rcases List.mem_cons.mp this with rfl | h
    · omega
    · exact h

theorem inv_new (hB : Boundary inside N B) {s e b : Nat} {bs : List Nat}
    (inv : Inv inside B s e (b :: bs)) (hnext : inside (e + 1) = false) :
    Inv inside B b b bs := by
  have hb : e < b := inv.bs_gt b (List.mem_cons_self ..)
  have hbB : b ∈ B := inv.bs_sub b (List.mem_cons_self ..)
  have hbin : inside b = true := hB.mem_inside b hbB
  have hsorted := List.pairwise_cons.mp inv.bs_sorted
  refine ⟨Nat.le_refl _, ?_, ?_, hbB, ?_, hsorted.1, hsorted.2, ?_⟩
  · intro x h1 h2
    have : x = b := by omega
    subst this; exact hbin
  · right
    have hne : b ≠ e + 1 := by
      intro h; subst h; simp [hbin] at hnext
    exact hole hB inv hnext (b - 1) (by omega) (by omega)
  · intro c hc; exact inv.bs_sub c (List.mem_cons_of_mem _ hc)
  · intro c hc hbc
    have := inv.gap c hc (by omega)
    rcases List.mem_cons.mp this with rfl | h
    · omega
    · exact h

/-- With nothing left in `B` above `e`, the run stops at `e`. -/
theorem stop_of_nil (hB : Boundary inside N B) {s e : Nat} (inv : Inv inside B s e []) :
    inside (e + 1) = false := by
  cases h : inside (e + 1) with
  | false => rfl
  | true =>
    exfalso
    obtain ⟨y, hy, hyin, hyout⟩ := exists_run_end hB (N - (e + 1)) (e + 1) (by have := hB.inside_lt _ h; omega) h
    have := inv.gap y (hB.end_mem y hyin hyout) (by omega)
    simp at this

theorem go_sound (hB : Boundary inside N B) :
    ∀ (bs : List Nat) (s e : Nat), Inv inside B s e bs →
      ∀ p ∈ go inside s e bs, ∀ x, p.1 ≤ x → x ≤ p.2 → inside x = true := by
  intro bs
  induction bs with
  | nil =>
    intro s e inv p hp x h1 h2
    simp [go] at hp; subst hp
    exact inv.run x h1 h2
  | cons b bs ih =>
    intro s e inv p hp x h1 h2
    by_cases hnext : inside (e + 1) = true
    · simp [go, hnext] at hp
      exact ih s b (inv_extend hB inv hnext) p hp x h1 h2
    · have hnext' : inside (e + 1) = false := by simpa using hnext
      simp [go, hnext'] at hp
      rcases hp with hp | hp
      · subst hp; exact inv.run x h1 h2
      · exact ih b b (inv_new hB inv hnext') p hp x h1 h2

theorem go_maximal (hB : Boundary inside N B) :
    ∀ (bs : List Nat) (s e : Nat), Inv inside B s e bs →
      ∀ p ∈ go inside s e bs, (p.1 = 0 ∨ inside (p.1 - 1) = false) ∧ inside (p.2 + 1) = false := by
  intro bs
  induction bs with
  | nil =>
    intro s e inv p hp
    simp [go] at hp; subst hp
    exact ⟨inv.start, stop_of_nil hB inv⟩
  | cons b bs ih =>
    intro s e inv p hp
    by_cases hnext : inside (e + 1) = true
    · simp [go, hnext] at hp
      exact ih s b (inv_extend hB inv hnext) p hp
    · have hnext' : inside (e + 1) = false := by simpa using hnext
      simp [go, hnext'] at hp
      rcases hp with hp | hp
      · subst hp; exact ⟨inv.start, hnext'⟩
      · exact ih b b (inv_new hB inv hnext') p hp

theorem go_endpoints_mem (hB : Boundary inside N B) :
    ∀ (bs : List Nat) (s e : Nat), Inv inside B s e bs → s ∈ B →
      ∀ p ∈ go inside s e bs, p.1 ∈ B ∧ p.2 ∈ B := by
  intro bs
  induction bs with
  | nil =>
    intro s e inv hs p hp
    simp [go] at hp; subst hp
    exact ⟨hs, inv.e_mem⟩
  | cons b bs ih =>
    intro s e inv hs p hp
    by_cases hnext : inside (e + 1) = true
    · simp [go, hnext] at hp
      exact ih s b (inv_extend hB inv hnext) hs p hp
    · have hnext' : inside (e + 1) = false := by simpa using hnext
      simp [go, hnext'] at hp
      rcases hp with hp | hp
      · subst hp; exact ⟨hs, inv.e_mem⟩
      · exact ih b b (inv_new hB inv hnext') (inv.bs_sub b (List.mem_cons_self ..)) p hp

theorem go_complete (hB : Boundary inside N B) :
    ∀ (bs : List Nat) (s e : Nat), Inv inside B s e bs →
      ∀ x, s ≤ x → inside x = true → ∃ p ∈ go inside s e bs, p.1 ≤ x ∧ x ≤ p.2 := by
  intro bs
  induction bs with
  | nil =>
    intro s e inv x hsx hx
    refine ⟨(s, e), by simp [go], hsx, ?_⟩
    apply Classical.byContradiction
    intro hcon
    have hxe : e < x := by omega
    obtain ⟨y, hy, hyin, hyout⟩ := exists_run_end hB (N - x) x (by have := hB.inside_lt _ hx; omega) hx
    have := inv.gap y (hB.end_mem y hyin hyout) (by omega)
    simp at this
  | cons b bs ih =>
    intro s e inv x hsx hx
    by_cases hnext : inside (e + 1) = true
    · obtain ⟨p, hp, h1, h2⟩ := ih s b (inv_extend hB inv hnext) x hsx hx
      exact ⟨p, by simpa [go, hnext] using hp, h1, h2⟩
    · have hnext' : inside (e + 1) = false := by simpa using hnext
      rcases Nat.lt_or_ge e x with hex | hxe
      · have hbx : b ≤ x := by
          apply Classical.byContradiction
          intro hcon
          have := hole hB inv hnext' x hex (by omega)
          simp [this] at hx
        obtain ⟨p, hp, h1, h2⟩ := ih b b (inv_new hB inv hnext') x hbx hx
        exact ⟨p, by simp [go, hnext']; exact Or.inr hp, h1, h2⟩
      · exact ⟨(s, e), by simp [go, hnext'], hsx, hxe⟩

theorem go_length : ∀ (bs : List Nat) (s e : Nat), (go inside s e bs).length ≤ bs.length + 1 := by
  intro bs
  induction bs with
  | nil => intro s e; simp [go]
  | cons b bs ih =>
    intro s e
    by_cases hnext : inside (e + 1) = true
    · simp [go, hnext]; have := ih s b; omega
    · have hnext' : inside (e + 1) = false := by simpa using hnext
      simp [go, hnext']; have := ih b b; omega

/-- The initial invariant: the first boundary distance opens the first run. -/
theorem inv_init (hB : Boundary inside N B) {b : Nat} {bs : List Nat} (hBeq : B = b :: bs) :
    Inv inside B b b bs := by
  have hsorted := List.pairwise_cons.mp (hBeq ▸ hB.sorted)
  have hbin : inside b = true := hB.mem_inside b (hBeq ▸ List.mem_cons_self ..)
  refine ⟨Nat.le_refl _, ?_, ?_, hBeq ▸ List.mem_cons_self .., ?_, hsorted.1, hsorted.2, ?_⟩
  · intro x h1 h2; have : x = b := by omega
    subst this; exact hbin
  · by_cases hb0 : b = 0
    · exact Or.inl hb0
    · right
      cases hprev : inside (b - 1) with
      | false => rfl
      | true =>
        exfalso
        obtain ⟨y, hy, hyin, hystart, _⟩ := exists_run_start (b - 1) hprev
        have hyB : y ∈ B := hB.start_mem y hyin hystart
        rw [hBeq] at hyB
        rcases List.mem_cons.mp hyB with rfl | hyB
        · omega
        · have := hsorted.1 y hyB; omega
  · intro c hc; rw [hBeq]; exact List.mem_cons_of_mem _ hc
  · intro c hc hbc
    rw [hBeq] at hc
    rcases List.mem_cons.mp hc with rfl | hc
    · omega
    · exact hc

/-- Every inside distance is at least the first boundary distance. -/
theorem head_le (hB : Boundary inside N B) {b : Nat} {bs : List Nat} (hBeq : B = b :: bs) :
    ∀ x, inside x = true → b ≤ x := by
  intro x hx
  obtain ⟨y, hy, hyin, hystart, _⟩ := exists_run_start x hx
  have hyB : y ∈ B := hB.start_mem y hyin hystart
  rw [hBeq] at hyB
  have hsorted := List.pairwise_cons.mp (hBeq ▸ hB.sorted)
  rcases List.mem_cons.mp hyB with rfl | hyB
  · exact hy
  · have := hsorted.1 y hyB; omega

/-! ### The lemma -/

/-- Every returned segment lies inside the query. -/
theorem segments_sound (hB : Boundary inside N B) :
    ∀ p ∈ segments inside B, ∀ x, p.1 ≤ x → x ≤ p.2 → inside x = true := by
  intro p hp
  cases hBeq : B with
  | nil => subst hBeq; simp [segments] at hp
  | cons b bs =>
    rw [hBeq] at hp
    exact go_sound hB bs b b (inv_init hB hBeq) p hp

/-- Every returned segment is maximal: its neighbours on the curve are outside. -/
theorem segments_maximal (hB : Boundary inside N B) :
    ∀ p ∈ segments inside B, (p.1 = 0 ∨ inside (p.1 - 1) = false) ∧ inside (p.2 + 1) = false := by
  intro p hp
  cases hBeq : B with
  | nil => subst hBeq; simp [segments] at hp
  | cons b bs =>
    rw [hBeq] at hp
    exact go_maximal hB bs b b (inv_init hB hBeq) p hp

/-- Segments start and end at boundary distances. -/
theorem segments_endpoints (hB : Boundary inside N B) :
    ∀ p ∈ segments inside B, p.1 ∈ B ∧ p.2 ∈ B := by
  intro p hp
  cases hBeq : B with
  | nil => subst hBeq; simp [segments] at hp
  | cons b bs =>
    rw [hBeq] at hp
    exact hBeq ▸ go_endpoints_mem hB bs b b (inv_init hB hBeq) (hBeq ▸ List.mem_cons_self ..) p hp

/-- Every inside distance is covered by a segment. -/
theorem segments_complete (hB : Boundary inside N B) :
    ∀ x, inside x = true → ∃ p ∈ segments inside B, p.1 ≤ x ∧ x ≤ p.2 := by
  intro x hx
  cases hBeq : B with
  | nil =>
    exfalso
    obtain ⟨y, _, hyin, hystart, _⟩ := exists_run_start x hx
    have := hB.start_mem y hyin hystart
    rw [hBeq] at this; simp at this
  | cons b bs =>
    have := go_complete hB bs b b (inv_init hB hBeq) x (head_le hB hBeq x hx) hx
    simpa [segments] using this

/-- There are at most `|B|` segments. -/
theorem segments_length_le : (segments inside B).length ≤ B.length := by
  cases B with
  | nil => simp [segments]
  | cons b bs => simp [segments]; exact go_length bs b b

/-- Proposition "Linear": the union of the segments is exactly the set of
distances inside the query, so the linear scheme on the curve issues one token
per query cell, as the native linear scheme does. -/
theorem linear_tokens (hB : Boundary inside N B) (x : Nat) :
    (∃ p ∈ segments inside B, p.1 ≤ x ∧ x ≤ p.2) ↔ inside x = true :=
  ⟨fun ⟨p, hp, h1, h2⟩ => segments_sound hB p hp x h1 h2, segments_complete hB x⟩

/-- Contiguity: a contiguous interval of inside distances lies within one segment. -/
theorem interval_subset_segment (hB : Boundary inside N B) {x y : Nat} (hxy : x ≤ y)
    (hall : ∀ z, x ≤ z → z ≤ y → inside z = true) :
    ∃ p ∈ segments inside B, p.1 ≤ x ∧ y ≤ p.2 := by
  obtain ⟨p, hp, h1, h2⟩ := segments_complete hB x (hall x (Nat.le_refl _) hxy)
  refine ⟨p, hp, h1, ?_⟩
  apply Classical.byContradiction
  intro hcon
  have hmax := (segments_maximal hB p hp).2
  have := hall (p.2 + 1) (by omega) (by omega)
  simp [this] at hmax

end Ers.Segments
