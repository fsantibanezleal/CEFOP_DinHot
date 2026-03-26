#pragma once

#include <vector>
#include <math.h>
#include <string.h>
#include <ctype.h>

#define PI (4.0f*atan(1.0f))

struct stVertex
{
	float x,y,z;
};

struct stFace
{
	unsigned dimension,vertex[4];
};
