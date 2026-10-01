# Editor bridges

Installed into a project from the app (**Connect engines** panel) or copied by hand:

| Engine | Copy this folder | To |
|--------|------------------|----|
| Unreal Engine 5 | `unreal/StoreListingKitBridge` | `<YourProject>/Plugins/StoreListingKitBridge` |
| Unity 2021.3+ | `unity/com.storelistingkit.bridge` | `<YourProject>/Packages/com.storelistingkit.bridge` |

Unreal: needs the *Python Editor Script Plugin* (ships with UE5; the bridge enables it as a dependency).
Menus appear under **Tools → Store Listing Kit** in both editors.
