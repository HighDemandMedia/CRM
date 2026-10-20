import { describe, expect, it } from 'vitest';
import { canFilterOwners, canChooseOwner } from './permissions.js';

describe('owner filter visibility', () => {
  it.each(['contacts', 'companies', 'deals', 'tasks', 'tickets', 'calendar', 'reports'])(
    'only offers filtering for team or organization scope in %s',
    (module) => {
      for (const scope of ['none', 'own', 'team', 'organization']) {
        expect(canFilterOwners({ rules: { [module]: { view: scope } } }, module)).toBe(
          ['team', 'organization'].includes(scope)
        );
      }
      expect(canFilterOwners(undefined, module)).toBe(false);
      expect(canFilterOwners({ rules: {} }, module)).toBe(false);
    }
  );
});

describe('owner picker visibility', () => {
  it.each(['contacts', 'companies', 'deals', 'tasks', 'tickets'])(
    'requires permission to assign other people in %s',
    (module) => {
      for (const scope of ['none', 'own', 'team', 'organization']) {
        expect(
          canChooseOwner({ rules: { [module]: { view: 'organization', reassign: scope } } }, module)
        ).toBe(['team', 'organization'].includes(scope));
      }
      expect(canChooseOwner(undefined, module)).toBe(false);
    }
  );
});
