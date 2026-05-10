/**
 * FavoritesContext compatibility layer.
 *
 * Previously used React Context API + useState.
 * Now delegates to Zustand (stores/favoritesStore) for fine-grained subscriptions
 * while keeping the same hook interface for consumers.
 */

import React from 'react'
import { useFavoritesStore } from '../stores/favoritesStore'

export const FavoritesProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // Provider is now a no-op because Zustand manages state outside React tree.
  // Kept here to avoid breaking existing tree structure.
  return <>{children}</>
}

export const useFavorites = () => {
  return useFavoritesStore()
}

export default FavoritesProvider
