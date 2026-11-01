/-!
# Executable semantics of the IEC 61131-3 standard function blocks used by
# the conformance suite

Each block is a deterministic state machine evaluated once per cycle:
`step : State → Inputs → Time → State × Outputs`, with time in
milliseconds (`Nat`). The definitions transcribe the ST bodies the standard
gives for the edge, bistable and counter blocks (IEC 61131-3 ed.3 tables 42
to 44) and the timing diagrams it gives for the timers (table 46), under the
discrete-time assumption stated in `SPEC.md` and the `.trace` comments: a
block sees the inputs of the cycle, is evaluated at the cycle's time
`t = cycle * period`, and an edge is seen at the first evaluation in which
the input has its new value.

The standard text itself is not available in this repository; the
transcription follows the derivations written in the `.trace` files. Two
readings that depend on the edition are isolated as parameters:
`CtuRule.pvMax` versus `CtuRule.pv` (ed.3 `CV < PVmax` versus FDIS 2001
`CV < PV`) and `fTrigInitM` (ed.3 `M := TRUE` versus FDIS 2001 `M := FALSE`).

No dependency on Mathlib: only core Lean 4.
-/

namespace Conformance

/-- A generic one-cycle block. -/
structure Block (S I O : Type) where
  init : S
  step : S → I → Nat → S × O

/-- Run a block over the cycle times and inputs, collecting the outputs. -/
def Block.run (b : Block S I O) : List (Nat × I) → List O
  | [] => []
  | (t, i) :: rest =>
    let (s', o) := b.step b.init i t
    o :: ({ b with init := s' }).run rest

/-! ## Timers (ed.3 table 46, timing diagrams) -/

/-- TON: `active` is "IN was TRUE at the previous evaluation and timing has
started", `tRise` the time of the rising edge. -/
structure TonState where
  active : Bool
  tRise : Nat
  deriving Repr, DecidableEq

/-- Output of a timer: (Q, ET in ms). -/
abbrev TimerOut := Bool × Nat

def tonStep (pt : Nat) (s : TonState) (inp : Bool) (t : Nat) : TonState × TimerOut :=
  if inp then
    let tr := if s.active then s.tRise else t
    let el := t - tr
    (⟨true, tr⟩, (decide (pt ≤ el), min el pt))
  else
    (⟨false, 0⟩, (false, 0))

def TON (pt : Nat) : Block TonState Bool TimerOut := ⟨⟨false, 0⟩, tonStep pt⟩

/-- TOF: `prevIn` remembers IN; `timing` is TRUE from the falling edge until
the next rising edge (while timing, ET = min(t - tFall, PT) and Q = (t - tFall < PT)). -/
structure TofState where
  prevIn : Bool
  timing : Bool
  tFall : Nat
  deriving Repr, DecidableEq

def tofStep (pt : Nat) (s : TofState) (inp : Bool) (t : Nat) : TofState × TimerOut :=
  if inp then
    (⟨true, false, 0⟩, (true, 0))
  else if s.prevIn then
    -- falling edge seen now
    (⟨false, true, t⟩, (true, 0))
  else if s.timing then
    let el := t - s.tFall
    (⟨false, true, s.tFall⟩, (decide (el < pt), min el pt))
  else
    (⟨false, false, 0⟩, (false, 0))

def TOF (pt : Nat) : Block TofState Bool TimerOut := ⟨⟨false, false, 0⟩, tofStep pt⟩

/-- TP phases: idle (no pulse), pulsing, done (pulse ended but IN still TRUE,
so no new pulse may start). -/
inductive TpPhase | idle | pulsing | done
  deriving Repr, DecidableEq

structure TpState where
  prevIn : Bool
  phase : TpPhase
  tRise : Nat
  deriving Repr, DecidableEq

def tpStep (pt : Nat) (s : TpState) (inp : Bool) (t : Nat) : TpState × TimerOut :=
  match s.phase with
  | .idle =>
    if inp && !s.prevIn then (⟨true, .pulsing, t⟩, (true, 0))
    else (⟨inp, .idle, 0⟩, (false, 0))
  | .pulsing =>
    let el := t - s.tRise
    if pt ≤ el then
      -- the pulse ends now; with IN FALSE the diagram shows ET returning to 0
      -- at the same instant, with IN TRUE it holds PT
      if inp then (⟨true, .done, s.tRise⟩, (false, pt))
      else (⟨false, .idle, 0⟩, (false, 0))
    else (⟨inp, .pulsing, s.tRise⟩, (true, el))
  | .done =>
    if inp then (⟨true, .done, s.tRise⟩, (false, pt))
    else (⟨false, .idle, 0⟩, (false, 0))

def TP (pt : Nat) : Block TpState Bool TimerOut := ⟨⟨false, .idle, 0⟩, tpStep pt⟩

/-! ## Edge detection (ed.3 table 43) -/

/-- `Q := CLK AND NOT M; M := CLK;` with M initially FALSE. -/
def rTrigStep (m : Bool) (clk : Bool) (_t : Nat) : Bool × Bool :=
  (clk, clk && !m)

def R_TRIG : Block Bool Bool Bool := ⟨false, rTrigStep⟩

/-- `Q := NOT CLK AND NOT M; M := NOT CLK;`. The initial value of M is the
edition-dependent point: ed.3 initialises it to TRUE (no edge on a first
evaluation with CLK FALSE), the FDIS 2001 text copied by matiec leaves it
FALSE. -/
def fTrigStep (m : Bool) (clk : Bool) (_t : Nat) : Bool × Bool :=
  (!clk, !clk && !m)

def F_TRIG (initM : Bool) : Block Bool Bool Bool := ⟨initM, fTrigStep⟩

/-! ## Bistables (ed.3 table 42) -/

/-- SR: `Q1 := S1 OR (NOT R AND Q1)`. Inputs (S1, R). -/
def srStep (q1 : Bool) (i : Bool × Bool) (_t : Nat) : Bool × Bool :=
  let q := i.1 || (!i.2 && q1)
  (q, q)

def SR : Block Bool (Bool × Bool) Bool := ⟨false, srStep⟩

/-- RS: `Q1 := NOT R1 AND (S OR Q1)`. Inputs (S, R1). -/
def rsStep (q1 : Bool) (i : Bool × Bool) (_t : Nat) : Bool × Bool :=
  let q := !i.2 && (i.1 || q1)
  (q, q)

def RS : Block Bool (Bool × Bool) Bool := ⟨false, rsStep⟩

/-! ## Counter (ed.3 table 44) -/

/-- Which bound the count-up test uses. -/
inductive CtuRule
  /-- ed.3: `CV < PVmax`, PVmax the maximum of the INT type. -/
  | pvMax
  /-- FDIS 2001 (matiec): `CV < PV`. -/
  | pv
  deriving Repr, DecidableEq

structure CtuState where
  prevCu : Bool
  cv : Nat
  deriving Repr, DecidableEq

/-- Inputs (CU, R); outputs (Q, CV). CV is kept as a `Nat` because the
traces only count upwards from 0; `pvMax = 32767` is INT's maximum. -/
def ctuStep (rule : CtuRule) (pv : Nat) (s : CtuState) (i : Bool × Bool) (_t : Nat) :
    CtuState × (Bool × Nat) :=
  let (cu, r) := i
  let edge := cu && !s.prevCu
  let bound := match rule with
    | .pvMax => 32767
    | .pv => pv
  let cv := if r then 0 else if edge && s.cv < bound then s.cv + 1 else s.cv
  (⟨cu, cv⟩, (decide (pv ≤ cv), cv))

def CTU (rule : CtuRule) (pv : Nat) : Block CtuState (Bool × Bool) (Bool × Nat) :=
  ⟨⟨false, 0⟩, ctuStep rule pv⟩

/-! ## Down and up-down counters (ed.3 table 44)

CV is an `Int` here because the CTD and CTUD traces count below 0. The
same `CtuRule` selects the bounds: ed.3 bounds the count by the INT range
(`PVmin = -32768`, `PVmax = 32767`), the FDIS 2001 body by `0` and `PV`. -/

def counterLo (rule : CtuRule) : Int := match rule with | .pvMax => -32768 | .pv => 0
def counterHi (rule : CtuRule) (pv : Int) : Int := match rule with | .pvMax => 32767 | .pv => pv

structure CtdState where
  prevCd : Bool
  cv : Int
  deriving Repr, DecidableEq

/-- CTD, inputs (CD, LD), outputs (Q, CV):
`IF LD THEN CV := PV; ELSIF CD AND (CV > PVmin) THEN CV := CV - 1; END_IF; Q := (CV <= 0);` -/
def ctdStep (rule : CtuRule) (pv : Int) (s : CtdState) (i : Bool × Bool) (_t : Nat) :
    CtdState × (Bool × Int) :=
  let (cd, ld) := i
  let edge := cd && !s.prevCd
  let cv := if ld then pv else if edge && counterLo rule < s.cv then s.cv - 1 else s.cv
  (⟨cd, cv⟩, (decide (cv ≤ 0), cv))

def CTD (rule : CtuRule) (pv : Int) : Block CtdState (Bool × Bool) (Bool × Int) :=
  ⟨⟨false, 0⟩, ctdStep rule pv⟩

structure CtudState where
  prevCu : Bool
  prevCd : Bool
  cv : Int
  deriving Repr, DecidableEq

/-- CTUD, inputs (CU, CD, R, LD), outputs (QU, QD, CV):
```
IF R THEN CV := 0;
ELSIF LD THEN CV := PV;
ELSE IF NOT (CU AND CD) THEN
  IF CU AND (CV < PVmax) THEN CV := CV + 1;
  ELSIF CD AND (CV > PVmin) THEN CV := CV - 1; END_IF; END_IF; END_IF;
QU := (CV >= PV); QD := (CV <= 0);
```
where CU and CD stand for their rising edges. -/
def ctudStep (rule : CtuRule) (pv : Int) (s : CtudState) (i : Bool × Bool × Bool × Bool)
    (_t : Nat) : CtudState × (Bool × Bool × Int) :=
  let (cu, cd, r, ld) := i
  let up := cu && !s.prevCu
  let down := cd && !s.prevCd
  let cv :=
    if r then 0
    else if ld then pv
    else if up && down then s.cv
    else if up && s.cv < counterHi rule pv then s.cv + 1
    else if down && counterLo rule < s.cv then s.cv - 1
    else s.cv
  (⟨cu, cd, cv⟩, (decide (pv ≤ cv), decide (cv ≤ 0), cv))

def CTUD (rule : CtuRule) (pv : Int) :
    Block CtudState (Bool × Bool × Bool × Bool) (Bool × Bool × Int) :=
  ⟨⟨false, false, 0⟩, ctudStep rule pv⟩

/-! ## Configurations: tasks and scheduling (ed.3 6.8.2, SPEC.md version 2)

A configuration is a list of tasks over shared globals `G` and the
programs' local state `L`. At a step at time `t`, a periodic task is due
when its interval divides `t`, a SINGLE task when its Boolean input has
risen since the previous step. Due tasks run one after the other in order
of priority (0 first); tasks of equal priority keep their declaration
order, which is the model's choice where the standard says nothing. -/

inductive Trigger (G : Type)
  /-- `TASK t(INTERVAL := ...)`, interval in ms. -/
  | periodic (intervalMs : Nat)
  /-- `TASK t(SINGLE := input)`: runs on a rising edge of `input`. -/
  | single (input : G → Bool)

structure Task (G L : Type) where
  priority : Nat
  trigger : Trigger G
  /-- The task's program: reads and writes the globals and the locals. -/
  run : G → L → G × L

structure ConfigState (G L : Type) where
  globals : G
  locals : L
  /-- Previous value of each task's SINGLE input (FALSE for periodic tasks),
  in task order. -/
  prevInput : List Bool

/-- (due now, input value to remember). -/
def Task.due (t : Task G L) (prev : Bool) (g : G) (time : Nat) : Bool × Bool :=
  match t.trigger with
  | .periodic i => (time % i == 0, false)
  | .single f => let now := f g; (now && !prev, now)

/-- Stable insertion by priority: a task goes after the tasks of lower or
equal priority number already placed. -/
def insertByPriority (x : Task G L) : List (Task G L) → List (Task G L)
  | [] => [x]
  | y :: ys => if y.priority ≤ x.priority then y :: insertByPriority x ys else x :: y :: ys

/-- Inserting the tasks in declaration order keeps that order among equal
priorities. -/
def sortByPriority (tasks : List (Task G L)) : List (Task G L) :=
  tasks.foldl (fun acc t => insertByPriority t acc) []

/-- One simulation step at time `time`. -/
def configStep (tasks : List (Task G L)) (s : ConfigState G L) (time : Nat) : ConfigState G L :=
  let flags := (tasks.zip s.prevInput).map fun (t, p) => t.due p s.globals time
  let dueTasks := ((tasks.zip flags).filter fun (_, f) => f.1).map (·.1)
  let (g, l) := (sortByPriority dueTasks).foldl (fun (g, l) t => t.run g l) (s.globals, s.locals)
  { globals := g, locals := l, prevInput := flags.map (·.2) }

/-- A configuration as a block: the step's inputs are written into the
globals first, the outputs are read after the last task. -/
def Config (tasks : List (Task G L)) (applyInput : I → G → G) (observe : G → L → O)
    (g₀ : G) (l₀ : L) : Block (ConfigState G L) I O :=
  ⟨⟨g₀, l₀, tasks.map fun _ => false⟩, fun s i t =>
    let s' := configStep tasks { s with globals := applyInput i s.globals } t
    (s', observe s'.globals s'.locals)⟩

/-! ### The suite's configurations (`conformance/config/`) -/

/-- `config/globals_external`: one program on a 100 ms task; globals
(g_in, g_cnt, g_sum), local n. -/
def globalsExternalCfg : Block (ConfigState (Int × Int × Int) Nat) Int (Int × Int × Nat) :=
  Config [⟨0, .periodic 100, fun (i, c, s) n => ((i, c + 1, s + i), n + 1)⟩]
    (fun i (_, c, s) => (i, c, s)) (fun (_, c, s) n => (c, s, n)) (0, 0, 1000) 0

/-- `config/two_periods`: fast (100 ms, priority 1) and slow (300 ms,
priority 2) counters in globals (fast_n, slow_n). -/
def twoPeriodsCfg : Block (ConfigState (Nat × Nat) Unit) Unit (Nat × Nat) :=
  Config [⟨1, .periodic 100, fun (f, s) u => ((f + 1, s), u)⟩,
          ⟨2, .periodic 300, fun (f, s) u => ((f, s + 1), u)⟩]
    (fun _ g => g) (fun g _ => g) (0, 0) ()

/-- `config/priority_order`: reader (declared first, priority 1) copies the
global g into its local seen; writer (priority 0) adds 10 to g. -/
def priorityOrderCfg : Block (ConfigState Nat Nat) Unit (Nat × Nat) :=
  Config [⟨1, .periodic 100, fun g _ => (g, g)⟩,
          ⟨0, .periodic 100, fun g seen => (g + 10, seen)⟩]
    (fun _ g => g) (fun g seen => (g, seen)) 0 0

/-- `config/global_exchange`: producer (200 ms, priority 0) increments cmd;
consumer (100 ms, priority 1) keeps (ack, changes). -/
def globalExchangeCfg : Block (ConfigState Nat (Nat × Nat)) Unit (Nat × Nat × Nat) :=
  Config [⟨0, .periodic 200, fun cmd l => (cmd + 1, l)⟩,
          ⟨1, .periodic 100, fun cmd (ack, ch) => (cmd, (cmd, if cmd == ack then ch else ch + 1))⟩]
    (fun _ g => g) (fun cmd (ack, ch) => (cmd, ack, ch)) 0 (0, 0)

/-- `config/event_single`: ticker (100 ms, priority 1) and an event task
(SINGLE := trig, priority 0); globals (trig, ev_n, tick_n). -/
def eventSingleCfg : Block (ConfigState (Bool × Nat × Nat) Unit) Bool (Nat × Nat) :=
  Config [⟨1, .periodic 100, fun (tr, e, k) u => ((tr, e, k + 1), u)⟩,
          ⟨0, .single (·.1), fun (tr, e, k) u => ((tr, e + 1, k), u)⟩]
    (fun tr (_, e, k) => (tr, e, k)) (fun (_, e, k) _ => (e, k)) (false, 0, 0) ()

/-- `undefined/tasks_same_priority`: two 100 ms tasks of priority 0 that
append their digit to marks; the model keeps declaration order. -/
def tasksSamePriorityCfg : Block (ConfigState Int Unit) Unit Int :=
  Config [⟨0, .periodic 100, fun m u => (m * 10 + 1, u)⟩,
          ⟨0, .periodic 100, fun m u => (m * 10 + 2, u)⟩]
    (fun _ g => g) (fun g _ => g) 0 ()

end Conformance
