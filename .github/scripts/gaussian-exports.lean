import Lean.Environment

open Lean

def exported (path : System.FilePath) : IO (Array ConstantInfo) := do
  let (mod, _) ← readModuleData path
  return mod.constants.filter fun c => !isPrivateName c.name && !c.name.isInternal

def main (args : List String) : IO Unit := do
  let before :: after :: names := args | throw <| IO.userError "expected paths and modules"
  for name in names do
    let left ← exported (System.FilePath.mk before / (name ++ ".olean"))
    let right ← exported (System.FilePath.mk after / (name ++ ".olean"))
    unless left.size == right.size do throw <| IO.userError s!"different public counts for {name}"
    for orig in left do
      let some next := right.find? (fun c => c.name == orig.name) | throw <| IO.userError s!"missing {orig.name}"
      unless orig.levelParams == next.levelParams && orig.type == next.type do
        throw <| IO.userError s!"different type or universe parameters for {orig.name}"
      if let .defnInfo a := orig then
        let .defnInfo b := next | throw <| IO.userError s!"no longer a definition: {orig.name}"
        unless a.value == b.value do throw <| IO.userError s!"definition value differs: {orig.name}"
    IO.println s!"{name}: {left.size} matching declarations."
