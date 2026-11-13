# 05: Startup eBay status sync with 24h cooldown, soft-deletes externally-ended

**What to build:** On app initialization, the frontend triggers an eBay status sync (reusing the existing sync-active GetSellerList logic) guarded by a 24h cooldown persisted like the existing quantity-refresh cooldown. Unlike the manual "Sync with eBay" button (unchanged, still marks items not_found), the startup sync soft-deletes any listing — including imported ones — that has an eBay listing ID but is no longer found on eBay (i.e. ended outside Axis Researcher). It returns a summary (e.g. how many listings were removed) for the toast system. The anti-mass-deactivation guard (abort when GetSellerList returns empty) must also protect this path. Cooldown failures (eBay unreachable) must not crash startup.

**Blocked by:** 03: Soft-delete mechanism + migration of existing not_found items

**Status:** done

- [ ] Startup sync runs at most once per 24h, tracked client-side like the quantity cooldown
- [ ] Externally-ended listings (including imported) are soft-deleted, not marked not_found
- [ ] Empty GetSellerList response aborts without hiding anything
- [ ] Endpoint returns counts of removed/updated listings; sync failure leaves app fully usable
- [ ] Manual "Sync with eBay" button behavior is unchanged and bypasses the cooldown
