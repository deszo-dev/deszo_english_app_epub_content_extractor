From Stdlib Require Import QArith.QArith.
From Stdlib Require Import Strings.String.

Open Scope string_scope.
Open Scope Q_scope.

Record TextBlock := {
  text : string;
  tag : string;
  position : nat;
  chapter_index : nat
}.

Record BlockFeatures := {
  length_chars : nat;
  alpha_ratio : Q;
  digit_ratio : Q;
  sentence_count : nat;
  has_dialogue_markers : bool
}.

Record Score := {
  base_score : Q;
  penalty : Q;
  boost : Q
}.

Inductive BlockDecision :=
| Keep
| Maybe
| Drop.

Definition final_score (s : Score) : Q :=
  s.(base_score) - s.(penalty) + s.(boost).

Definition classify_score (score : Q) : BlockDecision :=
  if Qlt_le_dec score 0 then Drop
  else if Qlt_le_dec score (3#10) then Maybe
  else Keep.

Definition alpha_penalty (f : BlockFeatures) : Q :=
  if Qlt_le_dec f.(alpha_ratio) (6#10) then (7#10) else 0.

Definition digit_penalty (f : BlockFeatures) : Q :=
  if Qlt_le_dec (3#10) f.(digit_ratio) then (6#10) else 0.

Theorem final_score_unfolds :
  forall s,
    final_score s = s.(base_score) - s.(penalty) + s.(boost).
Proof.
  reflexivity.
Qed.

Theorem keep_score_lower_bound :
  forall score,
    classify_score score = Keep ->
    (3#10 <= score)%Q.
Proof.
  intros score classified.
  unfold classify_score in classified.
  destruct (Qlt_le_dec score 0) as [lt_zero | ge_zero].
  - discriminate classified.
  - destruct (Qlt_le_dec score (3#10)) as [lt_keep | ge_keep].
    + discriminate classified.
    + exact ge_keep.
Qed.

Theorem drop_score_upper_bound :
  forall score,
    classify_score score = Drop ->
    (score < 0)%Q.
Proof.
  intros score classified.
  unfold classify_score in classified.
  destruct (Qlt_le_dec score 0) as [lt_zero | ge_zero].
  - exact lt_zero.
  - destruct (Qlt_le_dec score (3#10)) as [lt_keep | ge_keep].
    + discriminate classified.
    + discriminate classified.
Qed.
