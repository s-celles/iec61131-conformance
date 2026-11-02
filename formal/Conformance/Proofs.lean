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
instance : Matches (Option Int) Int := ⟨fun e a => match e with | none => true | some v => v == a⟩
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

/-- With the standard's initial `M = FALSE` (ed.3 table 45) the F_TRIG
trace holds ... -/
theorem f_trig_trace : conforms (F_TRIG false) fTrigInputs fTrigExpected = true := by decide
/-- ... and with `M := TRUE` it does not: that is the cycle-0 failure of the
runtimes that start M at TRUE. -/
theorem f_trig_trace_m_true : conforms (F_TRIG true) fTrigInputs fTrigExpected = false := by decide

/-- SR and RS share the input list; the expected pairs are (SR.Q1, RS.Q1). -/
def srRsExpectedSR : List (Option Bool) := srRsExpected.map (·.1)
def srRsExpectedRS : List (Option Bool) := srRsExpected.map (·.2)
theorem sr_trace : conforms SR srRsInputs srRsExpectedSR = true := by decide
theorem rs_trace : conforms RS srRsInputs srRsExpectedRS = true := by decide

/-- With ed.3's `CV < PVmax` the CTU trace holds ... -/
theorem ctu_trace_ed3 : conforms (CTU .pvMax 3) ctuInputs ctuExpected = true := by decide
/-- ... and with the FDIS 2001 `CV < PV` it does not (matiec's cycle-8 failure). -/
theorem ctu_trace_fdis : conforms (CTU .pv 3) ctuInputs ctuExpected = false := by decide

/-- CTD and CTUD likewise hold under ed.3's bounds and fail under the FDIS
2001 ones, each at the single cycle where CV goes below 0. -/
theorem ctd_trace_ed3 : conforms (CTD .pvMax 3) ctdInputs ctdExpected = true := by decide
theorem ctd_trace_fdis : conforms (CTD .pv 3) ctdInputs ctdExpected = false := by decide
theorem ctud_trace_ed3 : conforms (CTUD .pvMax 2) ctudInputs ctudExpected = true := by decide
theorem ctud_trace_fdis : conforms (CTUD .pv 2) ctudInputs ctudExpected = false := by decide

/-- At the INT bounds the two editions' conditions coincide (`CV < PVmax`
with PV = PVmax, `CV > PVmin` with PV = PVmin), so these traces hold under
both. IronPLC wraps instead (`findings.md`). -/
theorem ctud_bounds_trace_ed3 : conforms (CTUD .pvMax 32767) ctudBoundsInputs ctudBoundsExpected = true := by decide
theorem ctud_bounds_trace_fdis : conforms (CTUD .pv 32767) ctudBoundsInputs ctudBoundsExpected = true := by decide
theorem ctd_bounds_trace_ed3 : conforms (CTD .pvMax (-32768)) ctdBoundsInputs ctdBoundsExpected = true := by decide
theorem ctd_bounds_trace_fdis : conforms (CTD .pv (-32768)) ctdBoundsInputs ctdBoundsExpected = true := by decide

/-- Edge detectors started with CLK = TRUE: R_TRIG fires once, and F_TRIG's
output does not depend on its initial M here, so the trace holds for both
values (unlike `edge/f_trig` cycle 0). -/
def powerOnExpectedR : List (Option Bool) := powerOnExpected.map (·.1)
def powerOnExpectedF : List (Option Bool) := powerOnExpected.map (·.2)
theorem power_on_r_trig_trace : conforms R_TRIG powerOnInputs powerOnExpectedR = true := by decide
theorem power_on_f_trig_trace : conforms (F_TRIG false) powerOnInputs powerOnExpectedF = true := by decide
theorem power_on_f_trig_trace_m_true : conforms (F_TRIG true) powerOnInputs powerOnExpectedF = true := by decide

/-- Configurations (SPEC.md version 2): the task scheduler of
`Semantics.lean`, with priority order and declaration order on ties,
produces each `config/` trace; the equal-priority trace is what matiec
does and what the model's tie rule gives. -/
theorem globals_external_trace : conforms globalsExternalCfg globalsExternalInputs globalsExternalExpected = true := by decide
theorem two_periods_trace : conforms twoPeriodsCfg twoPeriodsInputs twoPeriodsExpected = true := by decide
theorem priority_order_trace : conforms priorityOrderCfg priorityOrderInputs priorityOrderExpected = true := by decide
theorem global_exchange_trace : conforms globalExchangeCfg globalExchangeInputs globalExchangeExpected = true := by decide
theorem event_single_trace : conforms eventSingleCfg eventSingleInputs eventSingleExpected = true := by decide
theorem tasks_same_priority_trace : conforms tasksSamePriorityCfg tasksSamePriorityInputs tasksSamePriorityExpected = true := by decide

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

/-- F_TRIG, first evaluation with CLK = FALSE: an edge with the standard's
`M = FALSE` (ed.3 table 45 and its NOTE), none with `M := TRUE`. This is the
whole of the runtimes' disagreement on `edge/f_trig`. -/
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

/-- CTD: load dominates, CV = PV after an evaluation with LD = TRUE. -/
theorem ctd_load_dominant (rule : CtuRule) (pv : Int) (s : CtdState) (cd : Bool) (t : Nat) :
    (ctdStep rule pv s (cd, true) t).2.2 = pv := by
  simp [ctdStep]

/-- CTD: Q is exactly `CV ≤ 0` after the evaluation. -/
theorem ctd_q_iff (rule : CtuRule) (pv : Int) (s : CtdState) (i : Bool × Bool) (t : Nat) :
    (ctdStep rule pv s i t).2.1 = decide ((ctdStep rule pv s i t).2.2 ≤ 0) := by
  rcases i with ⟨cd, ld⟩
  simp [ctdStep]

/-- CTUD: reset dominates load and counting, CV = 0 after R = TRUE. -/
theorem ctud_reset_dominant (rule : CtuRule) (pv : Int) (s : CtudState) (cu cd ld : Bool)
    (t : Nat) : (ctudStep rule pv s (cu, cd, true, ld) t).2.2.2 = 0 := by
  simp [ctudStep]

/-- CTUD: with R FALSE, load dominates counting, CV = PV after LD = TRUE. -/
theorem ctud_load_dominant (rule : CtuRule) (pv : Int) (s : CtudState) (cu cd : Bool)
    (t : Nat) : (ctudStep rule pv s (cu, cd, false, true) t).2.2.2 = pv := by
  simp [ctudStep]

/-- CTUD: simultaneous rising edges on CU and CD leave CV unchanged. -/
theorem ctud_both_edges_cancel (rule : CtuRule) (pv : Int) (s : CtudState) (t : Nat)
    (hu : s.prevCu = false) (hd : s.prevCd = false) :
    (ctudStep rule pv s (true, true, false, false) t).2.2.2 = s.cv := by
  simp [ctudStep, hu, hd]

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

/-- Scheduling: the writer (priority 0) runs before the reader (priority 1)
although it is declared second, so in every step the reader's local equals
the global just written. matiec, which runs tasks in declaration order,
violates this (`notes/comparison.md`, beremiz/matiec#43). -/
theorem priority_order_reader_sees_writer (s : ConfigState Nat Nat) (k : Nat)
    (h : s.prevInput = [false, false]) :
    let s' := configStep [⟨1, .periodic 100, fun g _ => (g, g)⟩,
                          ⟨0, .periodic 100, fun g seen => (g + 10, seen)⟩] s (k * 100)
    s'.locals = s'.globals := by
  simp [configStep, Task.due, h, sortByPriority, insertByPriority, Nat.mul_mod_left]

/-- A SINGLE task does not run while its input stays TRUE: with the input
already seen TRUE, the step leaves ev_n unchanged. -/
theorem single_task_needs_a_rising_edge (e k : Nat) :
    (configStep [⟨0, .single (·.1), fun (tr, e, k) u => ((tr, e + 1, k), u)⟩]
      ⟨(true, e, k), (), [true]⟩ 100).globals = (true, e, k) := by
  simp [configStep, Task.due, sortByPriority]

end Conformance
