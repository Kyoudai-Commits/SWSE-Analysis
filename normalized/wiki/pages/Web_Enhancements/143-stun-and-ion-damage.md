---
title: "Web Enhancements (Compilation) — Stun and Ion Damage"
parent_title: "Web Enhancements (Compilation)"
id: "wiki:Category:Web_Enhancements#143"
type: "compilation"
parent: "wiki:Category:Web_Enhancements"
heading: "Stun and Ion Damage"
heading_path: ["Web Enhancements (Compilation)", "Stun and Ion Damage"]
source_url: "https://swse.miraheze.org/wiki/Category:Web_Enhancements#Stun_and_Ion_Damage"
revision_id: "26287"
categories: ["Reference Books"]
---

# Stun and Ion Damage

[[Stun_Damage]] and [[Ion_Damage]] both received overhauls so they'd work better with the new [[Damage_Threshold]] and [[Condition_Track]] rules.

If a living target is hit by a [[Stun]] attack, compare the [[Stun_Damage]] (which is now the same as the weapon's normal damage) to the target's [[Damage_Threshold]]. If the [[Stun_Damage]] exceeds the [[Damage_Threshold]], the target moves 2 steps down the [[Condition_Track]]; otherwise, the attack has no additional effect. Half of the [[Stun_Damage]] is then subtracted from the target's Hit Points. To use a [[Stun]] weapon, a character must be within 6 squares of their target (except when they're using [[Stun_Grenades]], which create a radius effect).

[[Ion]] weapons work much the same way, except they affect only [[Droids]], [[Vehicles]], objects, and characters with cybernetic enhancements. In addition, [[Ion]] weapons can be fired at normal ranges and are not subject to the same 6-square limitation as [[Stun]] weapons.
