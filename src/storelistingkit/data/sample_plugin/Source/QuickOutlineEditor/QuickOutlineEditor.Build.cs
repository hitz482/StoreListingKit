using UnrealBuildTool;
public class QuickOutlineEditor : ModuleRules
{
	public QuickOutlineEditor(ReadOnlyTargetRules Target) : base(Target)
	{
		PrivateDependencyModuleNames.AddRange(new string[] { "Core", "UnrealEd", "QuickOutline" });
	}
}
