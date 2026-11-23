module

public import Formalism.PeriodIntegrals.SumAntidiagonalTuple
public import Mathlib.Algebra.BigOperators.Intervals
import Mathlib.Data.Finsupp.Multiset
import Mathlib.Data.Nat.Choose.Sum
import Mathlib.Data.Sym.Card

@[expose] public section

private theorem card_antidiagonalTuple (D k : ℕ) :
    (Finset.Nat.antidiagonalTuple D k).card = D.multichoose k := by
  rw [← Fintype.card_coe, ← Sym.card_sym_fin_eq_multichoose]
  apply Fintype.card_congr
  exact (Equiv.subtypeEquivRight (fun _ ↦ Finset.Nat.mem_antidiagonalTuple)).trans
    (Sym.equivNatSumOfFintype (Fin D) k).symm

theorem sum_antidiagonalTuple : PI.SumAntidiagonalTuple := by
  intro D T hDT
  obtain ⟨n, rfl⟩ := Nat.exists_eq_add_of_lt hDT
  rw [show D + n + 1 - D = n + 1 by omega, Nat.add_sub_cancel]
  simpa only [card_antidiagonalTuple, Nat.add_comm D n] using Nat.sum_range_multichoose n D
