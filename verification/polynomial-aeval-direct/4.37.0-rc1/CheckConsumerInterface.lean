import Lean

open Lean

def main (args : List String) : IO Unit := do
  let [oldFile, newFile] := args | throw <| IO.userError "two compiled module paths required"
  let (old, _) ← readModuleData oldFile
  let (new, _) ← readModuleData newFile
  let oldPublic := old.constants.filter fun c => !isPrivateName c.name
  let newPublic := new.constants.filter fun c => !isPrivateName c.name
  unless oldPublic.size == newPublic.size do
    throw <| IO.userError s!"public declaration count changed: {oldPublic.size} to {newPublic.size}"
  for decl in oldPublic do
    let some other := newPublic.find? (·.name == decl.name)
      | throw <| IO.userError s!"missing {decl.name}"
    unless decl.levelParams == other.levelParams && decl.type.equal other.type do
      throw <| IO.userError s!"type changed: {decl.name}"
  IO.println s!"identical compiled public names, universe parameters and types: {oldPublic.size}"
  IO.println "Import changes are checked separately against the source diff."
