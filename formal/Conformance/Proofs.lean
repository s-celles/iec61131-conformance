import Conformance.Semantics
import Conformance.Traces

/-!
# Theorems

Two kinds:

1. **Trace theorems**: each hand-written expected trace is exactly what the
   formal model produces (an expected value of `none`, i.e. `?` in the trace
   file, matches anything). These are checked by evaluation (`decide`), so
   they are only as strong as the model in `Semantics.lean`; what they rule
   out is an arithmetic slip or an inconsistency between the comment of a
   `.trace` file and its records.

2. **Property theorems**: facts about the models that hold for every state,
   input and time, which are the properties the differential run found
   IronPLC or matiec to violate.
-/

namespace Conformance

open Traces

/-- An expected output matches an actual one when every component that is
specified is equal. -/
class Matches (E A : Type) where
  ok : E → A → Bool

instance : Matches (Option Bool) Bool := ⟨fun e a => match e with | none => true | some v => v == a⟩
instance : Matches (Option Nat) Nat := ⟨fun e a => match e with | none => true | some v => v == a⟩
instance [Matches E₁ A₁] [Matches E₂ A₂] : Matches (E₁ × E₂) (A₁ × A₂) :=
  ⟨fun e a => Matches.ok e.1 a.1 && Matches.ok e.2 a.2⟩

/-- The block's run over the inputs matches the expected list, cycle by
cycle, and both lists have the same length. -/
def conforms [Matches E O] (b : Block S I O) (inputs : List (Nat × I)) (expected : List E) : Bool :=
  let rec go : List O → List E → Bool
    | [], [] => true
    | o :: os, e :: es => Matches.ok e o && go os es
    | _, _ => false
  go (b.run inputs) expected

/-! ## 1. The expected traces follow from the model -/

theorem ton_trace : conforms (TON 300) tonInputs tonExpected = true := by decide
theorem tof_trace : conforms (TOF 200) tofInputs tofExpected = true := by decide
theorem tp_trace : conforms (TP 300) tpInputs tpExpected = true := by decide
theorem r_trig_trace : conforms R_TRIG rTrigInputs rTrigExpected = true := by decide

/-- With ed.3's `M := TRUE` the F_TRIG trace holds ... -/
theorem f_trig_trace_ed3 : conforms (F_TRIG true) fTrigInputs fTrigExpected = true := by decide
/-- ... and with the FDIS 2001 initial value it does not (this is exactly
matiec's cycle-0 failure). -/
theorem f_trig_trace_fdis : conforms (F_TRIG false) fTrigInputs fTrigExpected = false := by decide

/-- SR and RS share the input list; the expected pairs are (SR.Q1, RS.Q1). -/
def srRsExpectedSR : List (Option Bool) := srRsExpected.map (·.1)
def srRsExpectedRS : List (Option Bool) := srRsExpected.map (·.2)
theorem sr_trace : conforms SR srRsInputs srRsExpectedSR = true := by decide
theorem rs_trace : conforms RS srRsInputs srRsExpectedRS = true := by decide

/-- With ed.3's `CV < PVmax` the CTU trace holds ... -/
theorem ctu_trace_ed3 : conforms (CTU .pvMax 3) ctuInputs ctuExpected = true := by decide
/-- ... and with the FDIS 2001 `CV < PV` it does not (matiec's cycle-8 failure). -/
theorem ctu_trace_fdis : conforms (CTU .pv 3) ctuInputs ctuExpected = false := by decide

/-! ## 2. Properties of the models

These are the properties the differential run showed one runtime violating
(see `notes/findings.md`). Each is stated for every state, input and time.
-/

/-- TON: whenever Q is TRUE, ET equals PT (the diagram never shows Q with
ET < PT). IronPLC violates this once PT is raised while Q is TRUE
(`undefined/ton_pt_change`), but that scenario changes `pt` between cycles,
which this model (fixed `pt`) does not cover: the theorem is about a
constant PT. -/
theorem ton_q_implies_et_eq_pt (pt : Nat) (s : TonState) (inp : Bool) (t : Nat) :
    (tonStep pt s inp t).2.1 = true → (tonStep pt s inp t).2.2 = pt := by
  unfold tonStep
  split
  · simp only [decide_eq_true_eq]
    intro h
    exact Nat.min_eq_right h
  · simp

/-- TON: ET never exceeds PT. -/
theorem ton_et_le_pt (pt : Nat) (s : TonState) (inp : Bool) (t : Nat) :
    (tonStep pt s inp t).2.2 ≤ pt := by
  unfold tonStep
  split
  · exact Nat.min_le_right _ _
  · exact Nat.zero_le _

/-- TOF at power-up: from the initial state, an evaluation with IN = FALSE
gives Q = FALSE and ET = 0, whatever the time. IronPLC violates this
(`findings.md` #1: it reports Q = TRUE). -/
theorem tof_initial_in_false_no_delay (pt t : Nat) :
    (tofStep pt (TOF pt).init false t).2 = (false, 0) := by
  simp [tofStep, TOF]

/-- TOF: Q is TRUE whenever IN is TRUE (the off-delay only ever delays the
falling edge). -/
theorem tof_in_true_q_true (pt : Nat) (s : TofState) (t : Nat) :
    (tofStep pt s true t).2.1 = true := by
  simp [tofStep]

/-- TP: once the pulse has ended with IN still TRUE (`done`), holding IN TRUE
never produces a new pulse: Q stays FALSE and the phase stays `done`.
IronPLC violates this (`findings.md` #2: it restarts the pulse). -/
theorem tp_no_retrigger_while_in_high (pt : Nat) (s : TpState) (t : Nat) (h : s.phase = .done) :
    (tpStep pt s true t).2.1 = false ∧ (tpStep pt s true t).1.phase = .done := by
  unfold tpStep
  rw [h]
  simp

/-- TP: in the `done` phase with IN FALSE the block returns to idle with ET = 0
(IronPLC keeps ET = PT instead, `findings.md` #3). -/
theorem tp_done_in_low_resets (pt : Nat) (s : TpState) (t : Nat) (h : s.phase = .done) :
    (tpStep pt s false t).2 = (false, 0) ∧ (tpStep pt s false t).1.phase = .idle := by
  unfold tpStep
  rw [h]
  simp

/-- TP: a rising edge of IN while pulsing is ignored: the phase stays
`pulsing` with the same start time as long as PT has not elapsed. -/
theorem tp_rising_edge_during_pulse_ignored (pt : Nat) (s : TpState) (inp : Bool) (t : Nat)
    (h : s.phase = .pulsing) (hel : t - s.tRise < pt) :
    (tpStep pt s inp t).1.phase = .pulsing ∧ (tpStep pt s inp t).1.tRise = s.tRise := by
  unfold tpStep
  rw [h]
  simp only
  have : ¬ pt ≤ t - s.tRise := Nat.not_le.mpr hel
  simp [this]

/-- R_TRIG: Q is never TRUE on two consecutive evaluations. -/
theorem r_trig_no_two_consecutive (m clk clk' : Bool) (t t' : Nat) :
    (rTrigStep m clk t).2 = true → (rTrigStep (rTrigStep m clk t).1 clk' t').2 = false := by
  simp [rTrigStep]
  intro hclk _
  simp [hclk]

/-- F_TRIG: Q is never TRUE on two consecutive evaluations. -/
theorem f_trig_no_two_consecutive (m clk clk' : Bool) (t t' : Nat) :
    (fTrigStep m clk t).2 = true → (fTrigStep (fTrigStep m clk t).1 clk' t').2 = false := by
  simp [fTrigStep]
  intro hclk _
  simp [hclk]

/-- F_TRIG, first evaluation with CLK = FALSE: no edge under ed.3's initial
`M := TRUE`, an edge under the FDIS 2001 `M := FALSE`. This is the whole of
the matiec/IronPLC disagreement on `edge/f_trig`. -/
theorem f_trig_first_eval_depends_on_init_m (t : Nat) :
    (fTrigStep true false t).2 = false ∧ (fTrigStep false false t).2 = true := by
  simp [fTrigStep]

/-- SR is set-dominant, RS is reset-dominant: with both inputs TRUE, from
any state, SR gives TRUE and RS gives FALSE. -/
theorem sr_set_dominant (q1 : Bool) (t : Nat) : (srStep q1 (true, true) t).2 = true := by
  simp [srStep]
theorem rs_reset_dominant (q1 : Bool) (t : Nat) : (rsStep q1 (true, true) t).2 = false := by
  simp [rsStep]

/-- CTU: Q is exactly `PV ≤ CV` after the evaluation, for either rule. -/
theorem ctu_q_iff (rule : CtuRule) (pv : Nat) (s : CtuState) (i : Bool × Bool) (t : Nat) :
    (ctuStep rule pv s i t).2.1 = decide (pv ≤ (ctuStep rule pv s i t).2.2) := by
  rcases i with ⟨cu, r⟩
  simp [ctuStep]

/-- CTU: reset dominates, CV = 0 after an evaluation with R = TRUE. -/
theorem ctu_reset_dominant (rule : CtuRule) (pv : Nat) (s : CtuState) (cu : Bool) (t : Nat) :
    (ctuStep rule pv s (cu, true) t).2.2 = 0 := by
  simp [ctuStep]

/-- CTU under the FDIS rule never counts above PV; this is why matiec stops at
CV = 3 for PV = 3 and never counts at PV = 0. -/
theorem ctu_fdis_cv_le_pv (pv : Nat) (s : CtuState) (i : Bool × Bool) (t : Nat)
    (h : s.cv ≤ pv) : (ctuStep .pv pv s i t).2.2 ≤ pv := by
  rcases i with ⟨cu, r⟩
  unfold ctuStep
  simp only
  split
  · exact Nat.zero_le _
  · split
    · rename_i hlt
      exact Nat.succ_le_of_lt (by simpa using (Bool.and_eq_true _ _ |>.mp hlt).2)
    · exact h

/-- TON switches at equality: when the elapsed time is exactly PT, Q is TRUE
on that very evaluation (RuSTy's `elapsed <= PT` test switches one cycle
later, `notes/comparison.md`). -/
theorem ton_q_at_exact_pt (pt tr : Nat) :
    (tonStep pt ⟨true, tr⟩ true (tr + pt)).2.1 = true := by
  simp [tonStep]

/-- TP: from idle, a rising edge always starts a pulse; in particular the
block never stays dead after a previous pulse (RuSTy, `notes/comparison.md`
item 2): the idle phase has no memory of past pulses. -/
theorem tp_idle_rising_edge_starts_pulse (pt tr t : Nat) :
    (tpStep pt ⟨false, .idle, tr⟩ true t).2 = (true, 0) ∧
    (tpStep pt ⟨false, .idle, tr⟩ true t).1.phase = .pulsing := by
  simp [tpStep]

end Conformance
