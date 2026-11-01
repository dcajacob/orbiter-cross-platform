// Copyright (c) Martin Schweiger
// Licensed under the MIT License

// shadow calculations


#include "Shadow.h"
#include <cstdlib>
#include <vector>

bool ccw( SurfacePoint2* P[], int i, int j, int k )
{
	float a = P[i]->x - P[j]->x;
	float b = P[i]->y - P[j]->y;
	float c = P[k]->x - P[j]->x;
	float d = P[k]->y - P[j]->y;

	return ( a*d - b*c <= 0 ); // TRUE if points i, j, k are counterclockwise
}




int cmpl( const void* a, const void* b )
{
    SurfacePoint2** pVertexPtrA = (SurfacePoint2**)a;
    SurfacePoint2** pVertexPtrB = (SurfacePoint2**)b;

	float vx = (*pVertexPtrA)->x - (*pVertexPtrB)->x;
	if( vx > 0.0f ) return 1;
	if( vx < 0.0f ) return -1;

	float vy = (*pVertexPtrB)->y - (*pVertexPtrA)->y;
	if( vy > 0.0f ) return 1;
	if( vy < 0.0f ) return -1;

	return 0;
}




int cmph( const void* a, const void* b )
{
	return cmpl( b, a );
}




UInt32 MakeChain(SurfacePoint2** pVertexPtrs, UInt32 dwNumVertexPtrs,
				 int (*cmp)(const void*, const void*) ) 
{
	UInt32 s = 1;

	qsort( pVertexPtrs, dwNumVertexPtrs, sizeof(SurfacePoint2*), cmp );
	
	for( UInt32 i=2; i<dwNumVertexPtrs; i++ )
	{
		UInt32 j = s;
		while( j>=1 && ccw( pVertexPtrs, i, j, j-1 ) )
			j--;

		s = j+1;

		// Swap the vertices s and i
		SurfacePoint2* tmp = pVertexPtrs[s];
		pVertexPtrs[s] = pVertexPtrs[i];
		pVertexPtrs[i] = tmp;
	}

	return s;
}




int ConvexHull2D( SurfacePoint2** pVertexPtrs, UInt32 dwNumVertexPtrs )
{
	if( !dwNumVertexPtrs )
		return 0;

	UInt32 cnt = 0;

	// Make lower hull
	cnt += MakeChain( &pVertexPtrs[0], dwNumVertexPtrs, cmpl );
	
	pVertexPtrs[dwNumVertexPtrs] = pVertexPtrs[0];
	
	// Make upper hull
	cnt += MakeChain( &pVertexPtrs[cnt], dwNumVertexPtrs-cnt+1, cmph );

	return cnt;
}



void Find2DConvexHull( UInt32 dwNumInVertices, SurfacePoint2* pInVertices,
					   UInt32* pdwNumOutIndices, UInt16** ppOutIndices )
{
	UInt32 i;
	// Separate typed buffers retain the original hull ordering without the
	// original unaligned pointer array inside a WORD byte buffer.
	static std::vector<UInt16> indices;
	static std::vector<SurfacePoint2*> vertices;
	indices.resize(dwNumInVertices+1);
	vertices.resize(dwNumInVertices+1);
	UInt16* pIndices=indices.data();
	SurfacePoint2** ppVertices=vertices.data();
	UInt32 dwNumIndices = 0;

	// The algorithm requires array of ptrs to vertices (for qsort) instead of
	// array of vertices, so do the conversion
    for (i = 0; i < dwNumInVertices; i++)
		ppVertices[i] = &pInVertices[i];

	dwNumIndices = ConvexHull2D( ppVertices, dwNumInVertices );

    // Convert back to array of indices
    for( i=0; i<dwNumIndices;i++ )
		pIndices[i] = (UInt16)( ppVertices[i] - &pInVertices[0] );

	(*pdwNumOutIndices) = dwNumIndices;
	(*ppOutIndices)     = pIndices;
}
