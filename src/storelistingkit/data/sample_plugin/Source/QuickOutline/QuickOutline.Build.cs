using UnrealBuildTool;

public class QuickOutline : ModuleRules
{
	public QuickOutline(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
		PublicDependencyModuleNames.AddRange(new string[] { "Core", "CoreUObject", "Engine", "RenderCore" });
		PrivateDependencyModuleNames.AddRange(new string[] { "Renderer", "Projects" });
	}
}
