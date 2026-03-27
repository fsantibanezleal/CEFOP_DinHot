# References

This page lists the key academic publications that inform the physics, algorithms, and design of the CEFOP DinHot application. The references are grouped by topic.

## Phase Retrieval -- The Gerchberg-Saxton Algorithm

1. **Gerchberg, R. W., & Saxton, W. O.** (1972).
   "A practical algorithm for the determination of phase from image and diffraction plane pictures."
   *Optik*, 35(2), 237-246.

   This paper introduced the iterative phase retrieval method that alternates between two conjugate planes (image and diffraction), applying known amplitude constraints in each domain. It is the foundation of the GS algorithm used in this project to compute SLM phase masks from desired trap intensity patterns.

2. **Leonardo, R. D., Ianni, F., & Ruocco, G.** (2007).
   "Computer generation of optimal holograms for optical trap arrays."
   *Optics Express*, 15(4), 1913-1922.
   DOI: [10.1364/OE.15.001913](https://doi.org/10.1364/OE.15.001913)

   This work extends the basic GS algorithm with an amplitude weighting scheme that significantly improves the uniformity of trap intensities across the array. The weighted update rule used in `PhaseMaskGenerator.calculate_phase_mask()` is directly based on this paper's approach.

3. **Fienup, J. R.** (1982).
   "Phase retrieval algorithms: a comparison."
   *Applied Optics*, 21(15), 2758-2769.
   DOI: [10.1364/AO.21.002758](https://doi.org/10.1364/AO.21.002758)

   A thorough comparison of several iterative phase retrieval methods, including error-reduction and input-output variants. This paper provides useful context for understanding the convergence properties and limitations of GS-type algorithms.

4. **Wyrowski, F., & Bryngdahl, O.** (1988).
   "Iterative Fourier-transform algorithm applied to computer holography."
   *Journal of the Optical Society of America A*, 5(7), 1058-1065.
   DOI: [10.1364/JOSAA.5.001058](https://doi.org/10.1364/JOSAA.5.001058)

   Demonstrates the application of iterative Fourier transform techniques to computing holograms, bridging the gap between phase retrieval theory and practical hologram generation for optical devices.

## Holographic Optical Tweezers

5. **Curtis, J. E., Koss, B. A., & Grier, D. G.** (2002).
   "Dynamic holographic optical tweezers."
   *Optics Communications*, 207(1-6), 169-175.
   DOI: [10.1016/S0030-4018(02)01524-9](https://doi.org/10.1016/S0030-4018(02)01524-9)

   This paper introduced the concept of dynamic holographic optical tweezers -- using a programmable SLM to create and reconfigure trap arrays in real time. The "DinHot" name of this project is derived from "Dynamic Holographic Tweezers" (or "Dinamicas Holograficas de Trampas" in Spanish). The paper demonstrated that trap patterns could be updated at video rates.

6. **Grier, D. G.** (2003).
   "A revolution in optical manipulation."
   *Nature*, 424, 810-816.
   DOI: [10.1038/nature01935](https://doi.org/10.1038/nature01935)

   A broad review covering the evolution of optical manipulation from single-beam tweezers to holographic multi-trap systems. It describes the physical principles behind trapping, the role of SLMs, and applications ranging from colloidal science to biology.

7. **Dufresne, E. R., & Grier, D. G.** (1998).
   "Optical tweezer arrays and optical substrates created with diffractive optics."
   *Review of Scientific Instruments*, 69(5), 1974-1977.
   DOI: [10.1063/1.1148883](https://doi.org/10.1063/1.1148883)

   An early demonstration of creating multiple simultaneous optical traps using diffractive optical elements. This work laid the groundwork for the SLM-based dynamic approach that followed.

## Spatial Light Modulators for Trapping

8. **Reicherter, M., Haist, T., Wagemann, E. U., & Tiziani, H. J.** (1999).
   "Optical particle trapping with computer-generated holograms written on a liquid-crystal display."
   *Optics Letters*, 24(9), 608-610.
   DOI: [10.1364/OL.24.000608](https://doi.org/10.1364/OL.24.000608)

   One of the first demonstrations of using a liquid-crystal SLM to display computer-generated holograms for optical trapping. This established the practical feasibility of the approach used in this project.

9. **Liesener, J., Reicherter, M., Haist, T., & Tiziani, H. J.** (2000).
   "Multi-functional optical tweezers using computer-generated holograms."
   *Optics Communications*, 185(1-3), 77-82.
   DOI: [10.1016/S0030-4018(00)00990-1](https://doi.org/10.1016/S0030-4018(00)00990-1)

   Extends SLM-based trapping to show that individual traps in a multi-trap array can be moved independently, which is the functionality provided by the "move" mode in CEFOP DinHot.

## Optical Trapping Physics

10. **Ashkin, A.** (1970).
    "Acceleration and trapping of particles by radiation pressure."
    *Physical Review Letters*, 24(4), 156-159.
    DOI: [10.1103/PhysRevLett.24.156](https://doi.org/10.1103/PhysRevLett.24.156)

    The foundational paper demonstrating that focused laser beams can exert measurable forces on microscopic particles. This work initiated the entire field of optical manipulation.

11. **Ashkin, A., Dziedzic, J. M., Bjorkholm, J. E., & Chu, S.** (1986).
    "Observation of a single-beam gradient force optical trap for dielectric particles."
    *Optics Letters*, 11(5), 288-290.
    DOI: [10.1364/OL.11.000288](https://doi.org/10.1364/OL.11.000288)

    First experimental observation of stable three-dimensional trapping using a single tightly focused laser beam -- the invention of optical tweezers as we know them today. All subsequent work on holographic tweezers builds upon this single-beam trapping concept.

## Optical Tweezers Reviews and Advanced Techniques

12. **Padgett, M. J. & Bowman, R.** (2011).
    "Tweezers with a twist."
    *Nature Photonics*, 5, 343-348.
    DOI: [10.1038/nphoton.2011.81](https://doi.org/10.1038/nphoton.2011.81)

    A review of optical tweezers that exploit orbital angular momentum (optical vortex beams) to rotate and manipulate microscopic particles. Covers how helical phase patterns `exp(i*l*theta)` create donut-shaped traps that transfer angular momentum to trapped objects, enabling controlled rotation and orbital motion.

13. **Jesacher, A., Schwaighofer, A., Furhapter, S., Maurer, C., Bernet, S. & Ritsch-Marte, M.** (2008).
    "Wavefront correction of spatial light modulators using an optical vortex image."
    *Optics Express*, 15(9), 5801-5808.
    DOI: [10.1364/OE.15.005801](https://doi.org/10.1364/OE.15.005801)

    Demonstrates a practical method for measuring and correcting the phase aberrations inherent in SLM devices using optical vortex images as wavefront sensors. The technique uses Zernike polynomial decomposition to characterize SLM non-uniformities and applies correction phases to the hologram, directly relevant to improving trap quality in real experimental setups.

14. **Roichman, Y. & Grier, D. G.** (2005).
    "Holographic assembly of quasicrystalline photonic heterostructures."
    *Optics Express*, 13(14), 5434-5439.
    DOI: [10.1364/OPEX.13.005434](https://doi.org/10.1364/OPEX.13.005434)

    Demonstrated the use of holographic optical tweezers to assemble complex three-dimensional structures from colloidal particles, including quasicrystalline arrangements. This work showcases the power of multi-trap holographic systems for materials science applications and validated the precision achievable with GS-optimized phase masks.
