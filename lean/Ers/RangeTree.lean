import Ers.CurveData

/-!
# Range trees are not relabelled by the curve (Proposition "Range trees")

On the order-2 curve in 2D, the box `[0,3] × [0,1]` (a product of dyadic
ranges, hence a vertex of the native range-tree product) is the two
non-adjacent runs `[0,3]` and `[12,15]` of distances, so no vertex of a binary
tree over the curve has it as its range (`box_not_interval`). The converse
inclusion does hold: every dyadic interval of the curve is a box whose sides
are dyadic ranges, i.e. a vertex of the product tree (`dyadic_are_products`,
checked for orders 2 and 3 in 2D and order 2 in 3D). The curve tree's
canonical ranges are therefore a strict subset of the product tree's, which
is why its index is smaller and its covers need more vertices.
-/

namespace Ers.RangeTree

open Ers.CurveData

def inBox (lo hi : List Nat) (c : List Nat) : Bool :=
  (c.zip (lo.zip hi)).all fun (x, l, h) => l ≤ x && x ≤ h

/-- Distances of the cells of a box. -/
def boxDistances (lo hi : List Nat) (curve : List (List Nat)) : List Nat :=
  ((List.range curve.length).zip curve).filterMap fun (x, c) => if inBox lo hi c then some x else none

/-- A list of distances is one interval iff it is contiguous. -/
def contiguous (xs : List Nat) : Bool :=
  match xs with
  | [] => true
  | x :: _ => xs.length == (xs.getLast? |>.getD x) + 1 - x

/-- The box `[0,3] × [0,1]` is not a curve interval ... -/
theorem box_not_interval : contiguous (boxDistances [0, 0] [3, 1] curve_2d_order2) = false := by decide

/-- ... its distances are the two runs `[0,3]` and `[12,15]`. -/
theorem box_distances : boxDistances [0, 0] [3, 1] curve_2d_order2 = [0, 1, 2, 3, 12, 13, 14, 15] := by decide

/-- A dyadic range: its length is a power of two and it starts at a multiple of its length. -/
def dyadic (lo hi : Nat) : Bool :=
  let len := hi + 1 - lo
  (List.range (len + 1)).any (fun k => 2 ^ k == len) && lo % len == 0

/-- The cells of a dyadic curve interval form a box whose every side is a dyadic range. -/
def intervalIsProductVertex (curve : List (List Nat)) (lo hi : Nat) : Bool :=
  let cells := (curve.drop lo).take (hi + 1 - lo)
  let d := (cells.headD []).length
  let sides := (List.range d).map fun i =>
    let coords := cells.map fun c => c.getD i 0
    (coords.foldr min (2 ^ 30), coords.foldr max 0)
  let volume := sides.foldr (fun (l, h) acc => (h + 1 - l) * acc) 1
  volume == cells.length && sides.all fun (l, h) => dyadic l h

/-- Every dyadic interval of the curve (every vertex of the binary tree over the
Hilbert domain) is a product-tree vertex. -/
def dyadicAreProducts (dn : Nat) (curve : List (List Nat)) : Bool :=
  (List.range (dn + 1)).all fun k =>
    let len := 2 ^ k
    (List.range (2 ^ (dn - k))).all fun i => intervalIsProductVertex curve (i * len) (i * len + len - 1)

theorem dyadic_are_products_2d_order2 : dyadicAreProducts 4 curve_2d_order2 = true := by decide
theorem dyadic_are_products_2d_order3 : dyadicAreProducts 6 curve_2d_order3 = true := by decide
theorem dyadic_are_products_3d_order2 : dyadicAreProducts 6 curve_3d_order2 = true := by decide

end Ers.RangeTree
